package main

import (
        "fmt"
        "html/template"
        "io"
        "net/http"
        "os"
        "path/filepath"
)

const (
        uploadDir = "./uploads"
        textFile  = "./shared.txt"
)

var page = template.Must(template.New("index").Parse(`
<!DOCTYPE html>
<html>
<head>
        <title>Simple Share</title>
</head>
<body>

<h2>Upload a file</h2>
<form enctype="multipart/form-data" action="/upload" method="post">
        <input type="file" name="file" required>
        <button type="submit">Upload</button>
</form>

<h2>Share text</h2>
<form action="/text" method="post">
        <textarea name="content" rows="10" cols="70" required></textarea><br>
        <button type="submit">Share Text</button>
</form>

<p><a href="/downloads/">View uploaded files</a></p>
<p><small>Text endpoint: /text</small></p>

</body>
</html>
`))

func main() {

        err := os.MkdirAll(uploadDir, 0755)
        if err != nil {
                panic(err)
        }

        http.HandleFunc("/", indexHandler)
        http.HandleFunc("/upload", uploadHandler)
        http.HandleFunc("/text", textHandler)

        // order matters
        http.HandleFunc("/download", listFilesHandler)
        http.HandleFunc("/download/", downloadHandler)

        fmt.Println("Listening on :8080")

        err = http.ListenAndServe(":8080", nil)
        if err != nil {
                panic(err)
        }
}

func indexHandler(w http.ResponseWriter, r *http.Request) {
        page.Execute(w, nil)
}

func uploadHandler(w http.ResponseWriter, r *http.Request) {

        file, header, err := r.FormFile("file")
        if err != nil {
                http.Error(w, "Invalid file upload", http.StatusBadRequest)
                return
        }
        defer file.Close()

        filename := filepath.Base(header.Filename)
        dstPath := filepath.Join(uploadDir, filename)

        dst, err := os.Create(dstPath)
        if err != nil {
                http.Error(w, "Cannot save file", http.StatusInternalServerError)
                return
        }
        defer dst.Close()

        _, err = io.Copy(dst, file)
        if err != nil {
                http.Error(w, "File write failed", http.StatusInternalServerError)
                return
        }

        http.Redirect(w, r, "/", http.StatusSeeOther)
}

func textHandler(w http.ResponseWriter, r *http.Request) {

        if r.Method == http.MethodPost {

                content := r.FormValue("content")
                if content == "" {
                        http.Error(w, "Empty text", http.StatusBadRequest)
                        return
                }

                err := os.WriteFile(textFile, []byte(content), 0644)
                if err != nil {
                        http.Error(w, "Cannot save text", http.StatusInternalServerError)
                        return
                }

                http.Redirect(w, r, "/", http.StatusSeeOther)
                return
        }

        data, err := os.ReadFile(textFile)
        if err != nil {
                http.NotFound(w, r)
                return
        }

        w.Header().Set("Content-Type", "text/plain; charset=utf-8")
        w.Write(data)
}

func listFilesHandler(w http.ResponseWriter, r *http.Request) {

        files, err := os.ReadDir(uploadDir)
        if err != nil {
                http.Error(w, "Cannot read upload directory", http.StatusInternalServerError)
                return
        }

        fmt.Fprintln(w, "<html><body>")
        fmt.Fprintln(w, "<h2>Uploaded Files</h2>")
        fmt.Fprintln(w, "<ul>")

        for _, f := range files {
                name := f.Name()
                fmt.Fprintf(w, `<li><a href="/download/%s">%s</a></li>`, name, name)
        }

        fmt.Fprintln(w, "</ul>")
        fmt.Fprintln(w, `<p><a href="/">Back</a></p>`)
        fmt.Fprintln(w, "</body></html>")
}

func downloadHandler(w http.ResponseWriter, r *http.Request) {

        filename := filepath.Base(r.URL.Path[len("/download/"):])
        if filename == "" {
                http.NotFound(w, r)
                return
        }

        filePath := filepath.Join(uploadDir, filename)

        file, err := os.Open(filePath)
        if err != nil {
                http.NotFound(w, r)
                return
        }
        defer file.Close()

        stat, err := file.Stat()
        if err != nil {
                http.NotFound(w, r)
                return
        }

        w.Header().Set("Content-Disposition", "attachment; filename=\""+filename+"\"")
        w.Header().Set("Content-Type", "application/octet-stream")
        w.Header().Set("Content-Length", fmt.Sprintf("%d", stat.Size()))

        http.ServeContent(w, r, filename, stat.ModTime(), file)
}
