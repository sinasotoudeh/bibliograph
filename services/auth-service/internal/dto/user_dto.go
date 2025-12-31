// internal/dto/user.go
package dto

import "time"

// User Response
type UserResponse struct {
	ID        string    `json:"id"`
	Email     string    `json:"email"`
	Name      string    `json:"name"`
	Role      string    `json:"role"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// Update Profile
type UpdateProfileRequest struct {
	Name  string `json:"name,omitempty"`
	Email string `json:"email,omitempty" validate:"omitempty,email"`
}

// Session Response
type SessionResponse struct {
	ID        string    `json:"id"`
	UserID    string    `json:"user_id"`
	IPAddress string    `json:"ip_address"`
	UserAgent string    `json:"user_agent"`
	CreatedAt time.Time `json:"created_at"`
	ExpiresAt time.Time `json:"expires_at"`
	IsActive  bool      `json:"is_active"`
}

// Upgrade Subscription
type UpgradeSubscriptionRequest struct {
	Plan string `json:"plan" validate:"required,oneof=premium enterprise"`
}
