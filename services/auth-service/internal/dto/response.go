// internal/dto/response.go
package dto

// Generic API Response
type APIResponse struct {
	Success bool        `json:"success"`
	Message string      `json:"message,omitempty"`
	Data    interface{} `json:"data,omitempty"`
	Error   *ErrorInfo  `json:"error,omitempty"`
}

// Error Information
type ErrorInfo struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Details string `json:"details,omitempty"`
}

// Error Response (for backward compatibility)
type ErrorResponse struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Details string `json:"details,omitempty"`
}

// Helper Functions
func NewSuccessResponse(data interface{}, message string) *APIResponse {
	return &APIResponse{
		Success: true,
		Message: message,
		Data:    data,
	}
}

func NewErrorResponse(code, message, details string) *APIResponse {
	return &APIResponse{
		Success: false,
		Error: &ErrorInfo{
			Code:    code,
			Message: message,
			Details: details,
		},
	}
}

// Common Success Responses
func SuccessWithData(data interface{}) *APIResponse {
	return NewSuccessResponse(data, "عملیات با موفقیت انجام شد")
}

func SuccessWithMessage(message string) *APIResponse {
	return NewSuccessResponse(nil, message)
}

// Common Error Responses
func BadRequest(message string) *APIResponse {
	return NewErrorResponse("BAD_REQUEST", message, "")
}

func Unauthorized(message string) *APIResponse {
	return NewErrorResponse("UNAUTHORIZED", message, "")
}

func NotFound(message string) *APIResponse {
	return NewErrorResponse("NOT_FOUND", message, "")
}

func InternalError(message string) *APIResponse {
	return NewErrorResponse("INTERNAL_ERROR", message, "")
}

func ValidationError(details string) *APIResponse {
	return NewErrorResponse("VALIDATION_ERROR", "خطای اعتبارسنجی", details)
}

func Forbidden(message string) *APIResponse {
	return NewErrorResponse("FORBIDDEN", message, "")
}

func Conflict(message string) *APIResponse {
	return NewErrorResponse("CONFLICT", message, "")
}
