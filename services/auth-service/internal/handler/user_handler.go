// internal/handler/user_handler.go
package handler

import (
	"encoding/json"
	"net/http"

	"github.com/go-playground/validator/v10"
	"github.com/gorilla/mux"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/dto"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/service"
	"github.com/sinas/bibliograph-ai/services/auth-service/pkg/logger"
	"go.uber.org/zap"
)

type UserHandler struct {
	userService service.UserService
	validator   *validator.Validate
}

// NewUserHandler creates a new user handler
func NewUserHandler(userService service.UserService, validator *validator.Validate) *UserHandler {
	return &UserHandler{
		userService: userService,
		validator:   validator,
	}
}

func (h *UserHandler) GetProfile(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("user_id").(string)

	user, err := h.userService.GetUserByID(r.Context(), userID)
	if err != nil {
		logger.Error("Failed to get user profile", zap.Error(err))
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(user)
}

func (h *UserHandler) UpdateProfile(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("user_id").(string)

	var req dto.UpdateUserRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		logger.Error("Failed to decode update request", zap.Error(err))
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	// Validate request
	if err := h.validator.Struct(req); err != nil {
		logger.Error("Validation failed", zap.Error(err))
		http.Error(w, "Validation failed", http.StatusBadRequest)
		return
	}

	if err := h.userService.UpdateUser(r.Context(), userID, &req); err != nil {
		logger.Error("Failed to update user", zap.Error(err))
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *UserHandler) DeleteAccount(w http.ResponseWriter, r *http.Request) {
	userID := r.Context().Value("user_id").(string)

	if err := h.userService.DeleteUser(r.Context(), userID); err != nil {
		logger.Error("Failed to delete user", zap.Error(err))
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func (h *UserHandler) GetUserByID(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	userID := vars["id"]

	user, err := h.userService.GetUserByID(r.Context(), userID)
	if err != nil {
		logger.Error("Failed to get user", zap.Error(err))
		http.Error(w, err.Error(), http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(user)
}


func (h *UserHandler) GetSessions(w http.ResponseWriter, r *http.Request) {
	// stub: return empty list
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode([]interface{}{})
}

func (h *UserHandler) UpgradeSubscription(w http.ResponseWriter, r *http.Request) {
	// stub: accept request but return 204
	w.WriteHeader(http.StatusNoContent)
}
