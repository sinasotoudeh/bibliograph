// internal/middleware/recovery.go
package middleware

import (
	"fmt"
	"net/http"
	"runtime/debug"

	"github.com/sinas/bibliograph-ai/services/auth-service/pkg/logger"
)

func Recoverer(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if err := recover(); err != nil {
				stack := debug.Stack()

				logger.Error("Panic recovered",
					logger.String("error", fmt.Sprintf("%v", err)),
					logger.String("stack", string(stack)),
					logger.String("method", r.Method),
					logger.String("path", r.URL.Path),
					logger.String("remote_addr", r.RemoteAddr),
				)

				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusInternalServerError)
				w.Write([]byte(fmt.Sprintf(`{
					"success": false,
					"error": "INTERNAL_SERVER_ERROR",
					"message": "An unexpected error occurred",
					"request_id": "%s"
				}`, w.Header().Get("X-Request-ID"))))
			}
		}()

		next.ServeHTTP(w, r)
	})
}
