// internal/middleware/rate_limit.go
package middleware

import (
	"fmt"
	"net/http"
	"strconv"
	"sync"
	"time"

	"github.com/sinas/bibliograph-ai/services/auth-service/pkg/logger"
)

type RateLimiter struct {
	requests map[string]*clientRequests
	mu       sync.RWMutex
	limit    int
	window   time.Duration
}

type clientRequests struct {
	count     int
	resetTime time.Time
}

func NewRateLimiter(limit int, window time.Duration) *RateLimiter {
	rl := &RateLimiter{
		requests: make(map[string]*clientRequests),
		limit:    limit,
		window:   window,
	}
	go rl.cleanup()
	return rl
}

func (rl *RateLimiter) cleanup() {
	ticker := time.NewTicker(time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		rl.mu.Lock()
		now := time.Now()
		for key, req := range rl.requests {
			if now.After(req.resetTime) {
				delete(rl.requests, key)
			}
		}
		rl.mu.Unlock()
	}
}

func (rl *RateLimiter) Allow(clientID string) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()
	req, exists := rl.requests[clientID]
	
	if !exists {
		rl.requests[clientID] = &clientRequests{
			count:     1,
			resetTime: now.Add(rl.window),
		}
		return true
	}

	if now.After(req.resetTime) {
		req.count = 1
		req.resetTime = now.Add(rl.window)
		return true
	}

	if req.count >= rl.limit {
		return false
	}

	req.count++
	return true
}

func (rl *RateLimiter) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		clientID := r.RemoteAddr

		if userID := r.Context().Value("user_id"); userID != nil {
			clientID = fmt.Sprintf("%v", userID)
		}

		if !rl.Allow(clientID) {
			logger.Warn("Rate limit exceeded",
				logger.String("client_id", clientID),
				logger.String("path", r.URL.Path),
				logger.Int("limit", rl.limit),
			)

			w.Header().Set("Content-Type", "application/json")
			w.Header().Set("X-RateLimit-Limit", strconv.Itoa(rl.limit))
			w.Header().Set("Retry-After", strconv.Itoa(int(rl.window.Seconds())))
			w.WriteHeader(http.StatusTooManyRequests)
			
			retryAfter := int(rl.window.Seconds())
			w.Write([]byte(fmt.Sprintf(`{
				"success": false,
				"error": "RATE_LIMIT_EXCEEDED",
				"message": "Too many requests. Please try again later.",
				"retry_after": %d
			}`, retryAfter)))
			return
		}

		next.ServeHTTP(w, r)
	})
}

func NewAPIRateLimiter() *RateLimiter {
	return NewRateLimiter(100, time.Minute)
}

func NewAuthRateLimiter() *RateLimiter {
	return NewRateLimiter(5, time.Minute)
}

func NewStrictRateLimiter() *RateLimiter {
	return NewRateLimiter(10, time.Minute)
}
