// internal/handler/response.go
package handler

import (
	"encoding/json"
	"net/http"

	"github.com/sinas/bibliograph-ai/services/auth-service/internal/dto"
)

// Response Helpers
func respondJSON(w http.ResponseWriter, statusCode int, data interface{}) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(data)
}

func respondError(w http.ResponseWriter, statusCode int, response *dto.APIResponse) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(statusCode)
	json.NewEncoder(w).Encode(response)
}

func respondValidationError(w http.ResponseWriter, details string) {
	respondError(w, http.StatusBadRequest, dto.ValidationError(details))
}

func respondSuccess(w http.ResponseWriter, data interface{}, message string) {
	response := dto.NewSuccessResponse(data, message)
	respondJSON(w, http.StatusOK, response)
}

func respondCreated(w http.ResponseWriter, data interface{}, message string) {
	response := dto.NewSuccessResponse(data, message)
	respondJSON(w, http.StatusCreated, response)
}

func respondBadRequest(w http.ResponseWriter, message string) {
	respondError(w, http.StatusBadRequest, dto.BadRequest(message))
}

func respondUnauthorized(w http.ResponseWriter, message string) {
	respondError(w, http.StatusUnauthorized, dto.Unauthorized(message))
}

func respondForbidden(w http.ResponseWriter, message string) {
	respondError(w, http.StatusForbidden, dto.Forbidden(message))
}

func respondNotFound(w http.ResponseWriter, message string) {
	respondError(w, http.StatusNotFound, dto.NotFound(message))
}

func respondConflict(w http.ResponseWriter, message string) {
	respondError(w, http.StatusConflict, dto.Conflict(message))
}

func respondInternalError(w http.ResponseWriter, message string) {
	respondError(w, http.StatusInternalServerError, dto.InternalError(message))
}
