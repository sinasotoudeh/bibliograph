package router

import (
	"context"
	"net/http"
	"strings"

	"github.com/gorilla/mux"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/domain"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/handler"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/middleware"
)

type Router struct {
	mux           *mux.Router
	authHandler   *handler.AuthHandler
	userHandler   *handler.UserHandler
	healthHandler *handler.HealthHandler
	jwtValidator  middleware.JWTValidator
}

func NewRouter(authHandler *handler.AuthHandler, userHandler *handler.UserHandler, healthHandler *handler.HealthHandler, jwtValidator middleware.JWTValidator) *Router {
	r := &Router{
		mux:           mux.NewRouter(),
		authHandler:   authHandler,
		userHandler:   userHandler,
		healthHandler: healthHandler,
		jwtValidator:  jwtValidator,
	}

	api := r.mux.PathPrefix("/api").Subrouter()

	// Public routes
	api.HandleFunc("/health", healthHandler.ServeReady).Methods("GET")
	api.HandleFunc("/register", authHandler.Register).Methods("POST")
	api.HandleFunc("/login", authHandler.Login).Methods("POST")
	api.HandleFunc("/refresh", authHandler.RefreshToken).Methods("POST")

	// Auth protected routes - middleware that uses jwtValidator
	authProtected := api.PathPrefix("/auth").Subrouter()
	authProtected.Use(r.authenticateMiddleware)
	authProtected.HandleFunc("/logout", authHandler.Logout).Methods("POST")
	authProtected.HandleFunc("/change-password", authHandler.ChangePassword).Methods("POST")

	// User routes (protected)
	user := api.PathPrefix("/user").Subrouter()
	user.Use(r.authenticateMiddleware)
	user.HandleFunc("/profile", userHandler.GetProfile).Methods("GET")
	user.HandleFunc("/profile", userHandler.UpdateProfile).Methods("PUT")
	user.HandleFunc("/sessions", userHandler.GetSessions).Methods("GET")
	user.HandleFunc("/upgrade", userHandler.UpgradeSubscription).Methods("POST")

	return r
}

// ServeHTTP implements http.Handler
func (r *Router) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	r.mux.ServeHTTP(w, req)
}

// authenticateMiddleware converts token header into context using jwtValidator
func (r *Router) authenticateMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, req *http.Request) {
		auth := req.Header.Get("Authorization")
		if auth == "" {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}
		parts := strings.Fields(auth)
		if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}
		token := parts[1]
		claims, err := r.jwtValidator.ValidateToken(token)
		if err != nil {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}
		// attach claims into context
		ctx := req.Context()
		ctx = contextWithClaims(ctx, claims)
		next.ServeHTTP(w, req.WithContext(ctx))
	})
}

// small helper to store claims in context
type ctxKey string

func contextWithClaims(ctx context.Context, claims *domain.Claims) context.Context {
	return context.WithValue(ctx, ctxKey("claims"), claims)
}
