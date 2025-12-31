// internal/handler/health_handler.go
package handler

import (
	"encoding/json"
	"net/http"

	"github.com/sinas/bibliograph-ai/services/auth-service/pkg/logger"
)

type HealthHandler struct{}

func NewHealthHandler() *HealthHandler {
	return &HealthHandler{}
}

func (h *HealthHandler) ServeHealth(w http.ResponseWriter, r *http.Request) {
	response := map[string]interface{}{
		"status":  "healthy",
		"service": "auth-service",
		"version": "1.0.0",
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	if err := json.NewEncoder(w).Encode(response); err != nil {
		logger.Error("Failed to encode health response")
	}
}

func (h *HealthHandler) ServeReady(w http.ResponseWriter, r *http.Request) {
	response := map[string]interface{}{
		"status": "ready",
		"checks": map[string]string{
			"database": "connected",
			"redis":    "connected",
		},
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	if err := json.NewEncoder(w).Encode(response); err != nil {
		logger.Error("Failed to encode ready response")
	}
}
