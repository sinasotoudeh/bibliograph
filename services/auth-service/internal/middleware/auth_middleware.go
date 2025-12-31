// internal/middleware/auth_middleware.go
package middleware

import (
	"context"
	"net/http"
	"strings"

	"github.com/sinas/bibliograph-ai/services/auth-service/internal/domain"
	"github.com/sinas/bibliograph-ai/services/auth-service/pkg/logger"
)

type JWTValidator interface {
	ValidateToken(token string) (*domain.Claims, error)
}

type AuthMiddleware struct {
	jwtValidator JWTValidator
}

func NewAuthMiddleware(jwtValidator JWTValidator) *AuthMiddleware {
	return &AuthMiddleware{
		jwtValidator: jwtValidator,
	}
}

func (m *AuthMiddleware) Authenticate(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		authHeader := r.Header.Get("Authorization")

		if authHeader == "" {
			logger.Warn("Missing authorization header")
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}

		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			logger.Warn("Invalid authorization header format")
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}

		token := parts[1]
		claims, err := m.jwtValidator.ValidateToken(token)
		if err != nil {
			logger.Warn("Invalid token", logger.Err(err))
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}

		logger.Debug("User authenticated", 
			logger.String("user_id", claims.UserID.String()))

		ctx := context.WithValue(r.Context(), "user_id", claims.UserID.String())
		ctx = context.WithValue(ctx, "email", claims.Email)
		ctx = context.WithValue(ctx, "role", string(claims.Role))

		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func (m *AuthMiddleware) RequireRole(role string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			userRole, ok := r.Context().Value("role").(string)

			if !ok || userRole != role {
				logger.Warn("Insufficient permissions",
					logger.String("required", role),
					logger.String("actual", userRole))
				http.Error(w, "Forbidden", http.StatusForbidden)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}
