package dto

// AuthResponse returned after register/login/refresh
type AuthResponse struct {
	AccessToken  string       `json:"access_token"`
	RefreshToken string       `json:"refresh_token"`
	ExpiresIn    int64        `json:"expires_in"`
	User         UserResponse `json:"user"`
}

// UpdateUserRequest for updating profile fields
type UpdateUserRequest struct {
	Email *string `json:"email,omitempty" validate:"omitempty,email"`
	Name  *string `json:"name,omitempty"`
	Role  *string `json:"role,omitempty" validate:"omitempty,oneof=researcher translator publisher student"`
}
