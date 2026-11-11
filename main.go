// DEADFRAME — serveur de jeu LAN (sert le jeu + relais multijoueur WebSocket).
// Aucune dépendance externe : bibliothèque standard Go uniquement.
package main

import (
	"bufio"
	"crypto/sha1"
	"embed"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"strings"
	"sync"
	"time"
)

//go:embed index.html
var indexHTML []byte

//go:embed assets
var assetsFS embed.FS

type client struct {
	id   int
	conn net.Conn
	out  chan []byte
}

var (
	mu      sync.Mutex
	clients = map[int]*client{}
	nextID  = 1
	port    int
)

func hostID() int { // appelé sous verrou
	h := 0
	for id := range clients {
		if h == 0 || id < h {
			h = id
		}
	}
	return h
}

func broadcast(msg []byte, except int) {
	mu.Lock()
	defer mu.Unlock()
	for id, c := range clients {
		if id == except {
			continue
		}
		select {
		case c.out <- msg:
		default: // client trop lent : on jette le paquet
		}
	}
}

func frame(payload []byte) []byte {
	n := len(payload)
	var h []byte
	switch {
	case n < 126:
		h = []byte{0x81, byte(n)}
	case n < 65536:
		h = []byte{0x81, 126, byte(n >> 8), byte(n)}
	default:
		h = make([]byte, 10)
		h[0], h[1] = 0x81, 127
		binary.BigEndian.PutUint64(h[2:], uint64(n))
	}
	return append(h, payload...)
}

func readFrame(br *bufio.Reader) (op byte, fin bool, payload []byte, err error) {
	var h [2]byte
	if _, err = io.ReadFull(br, h[:]); err != nil {
		return
	}
	fin = h[0]&0x80 != 0
	op = h[0] & 0x0f
	masked := h[1]&0x80 != 0
	n := uint64(h[1] & 0x7f)
	if n == 126 {
		var b [2]byte
		if _, err = io.ReadFull(br, b[:]); err != nil {
			return
		}
		n = uint64(binary.BigEndian.Uint16(b[:]))
	} else if n == 127 {
		var b [8]byte
		if _, err = io.ReadFull(br, b[:]); err != nil {
			return
		}
		n = binary.BigEndian.Uint64(b[:])
	}
	if n > 1<<16 {
		err = errors.New("frame too large")
		return
	}
	var mask [4]byte
	if masked {
		if _, err = io.ReadFull(br, mask[:]); err != nil {
			return
		}
	}
	payload = make([]byte, n)
	if _, err = io.ReadFull(br, payload); err != nil {
		return
	}
	if masked {
		for i := range payload {
			payload[i] ^= mask[i&3]
		}
	}
	return
}

func wsHandler(w http.ResponseWriter, r *http.Request) {
	key := r.Header.Get("Sec-WebSocket-Key")
	if !strings.EqualFold(r.Header.Get("Upgrade"), "websocket") || key == "" {
		http.Error(w, "websocket only", http.StatusBadRequest)
		return
	}
	hj, ok := w.(http.Hijacker)
	if !ok {
		http.Error(w, "no hijack", http.StatusInternalServerError)
		return
	}
	conn, rw, err := hj.Hijack()
	if err != nil {
		return
	}
	defer conn.Close()
	sum := sha1.Sum([]byte(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))
	fmt.Fprintf(rw, "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n\r\n",
		base64.StdEncoding.EncodeToString(sum[:]))
	if rw.Flush() != nil {
		return
	}

	mu.Lock()
	if len(clients) >= 16 {
		mu.Unlock()
		return
	}
	c := &client{id: nextID, conn: conn, out: make(chan []byte, 512)}
	nextID++
	clients[c.id] = c
	host := hostID()
	n := len(clients)
	mu.Unlock()
	fmt.Printf("  [+] joueur #%d connecté (%s) — %d en ligne\n", c.id, conn.RemoteAddr(), n)

	done := make(chan struct{})
	go func() { // écrivain
		for {
			select {
			case m := <-c.out:
				conn.SetWriteDeadline(time.Now().Add(5 * time.Second))
				if _, err := conn.Write(m); err != nil {
					conn.Close()
					return
				}
			case <-done:
				return
			}
		}
	}()
	c.out <- frame([]byte(fmt.Sprintf(`{"f":0,"d":{"t":"hi","id":%d,"host":%d}}`, c.id, host)))
	broadcast(frame([]byte(fmt.Sprintf(`{"f":0,"d":{"t":"join","id":%d,"host":%d}}`, c.id, host))), c.id)

	var frag []byte
	for {
		conn.SetReadDeadline(time.Now().Add(30 * time.Second))
		op, fin, p, err := readFrame(rw.Reader)
		if err != nil || op == 8 {
			break
		}
		switch op {
		case 9: // ping
			pong := append([]byte{0x8A, byte(len(p) & 0x7f)}, p[:len(p)&0x7f]...)
			select {
			case c.out <- pong:
			default:
			}
			continue
		case 10:
			continue
		case 0:
			frag = append(frag, p...)
		default:
			frag = append(frag[:0], p...)
		}
		if !fin || len(frag) > 1<<16 {
			if len(frag) > 1<<16 {
				break
			}
			continue
		}
		if len(frag) > 0 && frag[0] == '{' && json.Valid(frag) {
			msg := make([]byte, 0, len(frag)+24)
			msg = append(msg, fmt.Sprintf(`{"f":%d,"d":`, c.id)...)
			msg = append(msg, frag...)
			msg = append(msg, '}')
			broadcast(frame(msg), c.id)
		}
		frag = frag[:0]
	}

	close(done)
	mu.Lock()
	delete(clients, c.id)
	host = hostID()
	n = len(clients)
	mu.Unlock()
	fmt.Printf("  [-] joueur #%d déconnecté — %d en ligne\n", c.id, n)
	broadcast(frame([]byte(fmt.Sprintf(`{"f":0,"d":{"t":"leave","id":%d,"host":%d}}`, c.id, host))), 0)
}

func lanURLs() []string {
	var out []string
	addrs, _ := net.InterfaceAddrs()
	for _, a := range addrs {
		if ipn, ok := a.(*net.IPNet); ok && !ipn.IP.IsLoopback() {
			if ip4 := ipn.IP.To4(); ip4 != nil && !ip4.IsLinkLocalUnicast() {
				out = append(out, fmt.Sprintf("http://%s:%d", ip4, port))
			}
		}
	}
	return out
}

func openBrowser(url string) {
	switch runtime.GOOS {
	case "windows":
		// fenêtre "application" sans barre d'adresse si Edge/Chrome est présent
		for _, c := range []string{
			os.Getenv("ProgramFiles(x86)") + `\Microsoft\Edge\Application\msedge.exe`,
			os.Getenv("ProgramFiles") + `\Microsoft\Edge\Application\msedge.exe`,
			os.Getenv("ProgramFiles") + `\Google\Chrome\Application\chrome.exe`,
			os.Getenv("ProgramFiles(x86)") + `\Google\Chrome\Application\chrome.exe`,
			os.Getenv("LocalAppData") + `\Google\Chrome\Application\chrome.exe`,
		} {
			if st, err := os.Stat(c); err == nil && !st.IsDir() {
				if exec.Command(c, "--app="+url, "--start-maximized").Start() == nil {
					return
				}
			}
		}
		exec.Command("rundll32", "url.dll,FileProtocolHandler", url).Start()
	case "darwin":
		exec.Command("open", url).Start()
	default:
		exec.Command("xdg-open", url).Start()
	}
}

func main() {
	p := flag.Int("port", 7777, "port d'écoute")
	noOpen := flag.Bool("noopen", false, "ne pas ouvrir le jeu automatiquement (serveur dédié)")
	flag.Parse()

	mux := http.NewServeMux()
	mux.HandleFunc("/ws", wsHandler)
	mux.HandleFunc("/info", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		mu.Lock()
		n := len(clients)
		mu.Unlock()
		json.NewEncoder(w).Encode(map[string]any{"urls": lanURLs(), "players": n})
	})
	mux.Handle("/assets/", http.FileServer(http.FS(assetsFS)))
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Header().Set("Cache-Control", "no-store")
		w.Write(indexHTML)
	})

	var ln net.Listener
	var err error
	for port = *p; port < *p+10; port++ {
		if ln, err = net.Listen("tcp", fmt.Sprintf(":%d", port)); err == nil {
			break
		}
	}
	if err != nil {
		fmt.Println("Impossible d'ouvrir un port :", err)
		fmt.Println("Appuie sur Entrée pour quitter.")
		fmt.Scanln()
		return
	}

	local := fmt.Sprintf("http://localhost:%d", port)
	fmt.Println()
	fmt.Println("  ██████  DEADFRAME  ██████   serveur de jeu")
	fmt.Println("  ----------------------------------------------")
	fmt.Println("  Toi          :", local)
	urls := lanURLs()
	if len(urls) == 0 {
		fmt.Println("  Tes amis     : (aucun réseau local détecté)")
	}
	for _, u := range urls {
		fmt.Println("  Tes amis     :", u, "  (même Wi-Fi / réseau)")
	}
	fmt.Println("  ----------------------------------------------")
	fmt.Println("  Laisse cette fenêtre ouverte pendant la partie.")
	fmt.Println("  Ferme-la pour arrêter le serveur.")
	fmt.Println()
	if !*noOpen {
		go func() { time.Sleep(300 * time.Millisecond); openBrowser(local) }()
	}
	http.Serve(ln, mux)
}
