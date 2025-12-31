// internal/handler/auth_handler.go
package handler

import (
	"encoding/json"
	"net/http"

	"github.com/go-playground/validator/v10"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/dto"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/service"
	"github.com/sinas/bibliograph-ai/services/auth-service/pkg/logger"
	"go.uber.org/zap"
)

type AuthHandler struct {
	authService service.AuthService
	validator   *validator.Validate
}

// NewAuthHandler creates a new auth handler
func NewAuthHandler(authService service.AuthService, validator *validator.Validate) *AuthHandler {
	return &AuthHandler{
		authService: authService,
		validator:   validator,
	}
}

func (h *AuthHandler) Register(w http.ResponseWriter, r *http.Request) {
	var req dto.RegisterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error("Failed to decode register request", zap.Error(err))
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	// Validate request
	if err := h.validator.Struct(req); err != nil {
		logger.Error("Validation failed", zap.Error(err))
		http.Error(w, "Validation failed", http.StatusBadRequest)
		return
	}

	response, err := h.authService.Register(r.Context(), &req)
	if err != nil {
		logger.Error("Registration failed", zap.Error(err))
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(response)
}

func (h *AuthHandler) Login(w http.ResponseWriter, r *http.Request) {
	var req dto.LoginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error("Failed to decode login request", zap.Error(err))
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	// Validate request
	if err := h.validator.Struct(req); err != nil {
		logger.Error("Validation failed", zap.Error(err))
		http.Error(w, "Validation failed", http.StatusBadRequest)
		return
	}

	response, err := h.authService.Login(r.Context(), &req)
	if err != nil {
		logger.Error("Login failed", zap.Error(err))
		http.Error(w, err.Error(), http.StatusUnauthorized)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func (h *AuthHandler) RefreshToken(w http.ResponseWriter, r *http.Request) {
	var req dto.RefreshTokenRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error("Failed to decode refresh token request", zap.Error(err))
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	// Validate request
	if err := h.validator.Struct(req); err != nil {
		logger.Error("Validation failed", zap.Error(err))
		http.Error(w, "Validation failed", http.StatusBadRequest)
		return
	}

	response, err := h.authService.RefreshToken(r.Context(), req.RefreshToken)
	if err != nil {
		logger.Error("Token refresh failed", zap.Error(err))
		http.Error(w, err.Error(), http.StatusUnauthorized)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func (h *AuthHandler) Logout(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("user_id").(string)
	sessionID := r.Header.Get("X-Session-ID")

	if err := h.authService.Logout(r.Context(), userID, sessionID); err != nil {
		logger.Error("Logout failed", zap.Error(err))
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *AuthHandler) ChangePassword(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("user_id").(string)

	var req dto.ChangePasswordRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error("Failed to decode change password request", zap.Error(err))
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	// Validate request
	if err := h.validator.Struct(req); err != nil {
		logger.Error("Validation failed", zap.Error(err))
		http.Error(w, "Validation failed", http.StatusBadRequest)
		return
	}

	if err := h.authService.ChangePassword(r.Context(), userID, &req); err != nil {
		logger.Error("Password change failed", zap.Error(err))
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}
