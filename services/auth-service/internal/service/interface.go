// internal/service/interface.go
package service

import (
	"context"

	"github.com/sinas/bibliograph-ai/services/auth-service/internal/domain"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/dto"
)

// AuthService تعریف سرویس احراز هویت
type AuthService interface {
	Register(ctx context.Context, req *dto.RegisterRequest) (*dto.AuthResponse, error)
	Login(ctx context.Context, req *dto.LoginRequest) (*dto.AuthResponse, error)
	RefreshToken(ctx context.Context, refreshToken string) (*dto.AuthResponse, error)
	Logout(ctx context.Context, userID string, sessionID string) error
	ChangePassword(ctx context.Context, userID string, req *dto.ChangePasswordRequest) error
}

// UserService تعریف سرویس کاربر
type UserService interface {
	GetUserByID(ctx context.Context, userID string) (*domain.User, error)
	UpdateUser(ctx context.Context, userID string, req *dto.UpdateUserRequest) error
	DeleteUser(ctx context.Context, userID string) error
}
