package service

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/domain"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/dto"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/repository"
	"github.com/sinas/bibliograph-ai/services/auth-service/pkg/logger"
)

// authService پیاده‌سازی concrete از AuthService
type authService struct {
	userRepo    repository.UserRepository
	sessionRepo repository.SessionRepository
	jwtHelper   JWTHelper
}

// سازنده
func NewAuthService(userRepo repository.UserRepository, sessionRepo repository.SessionRepository, jwtHelper JWTHelper) AuthService {
	return &authService{
		userRepo:    userRepo,
		sessionRepo: sessionRepo,
		jwtHelper:   jwtHelper,
	}
}

// ✅ Register
func (s *authService) Register(ctx context.Context, req *dto.RegisterRequest) (*dto.AuthResponse, error) {
	logger.Info("User registration attempt", logger.String("email", req.Email))

	if _, err := s.userRepo.FindByEmail(ctx, req.Email); err == nil {
		return nil, fmt.Errorf("user already exists")
	}

	hashed, err := s.jwtHelper.HashPassword(req.Password)
	if err != nil {
		return nil, fmt.Errorf("failed to hash password: %v", err)
	}

	user := &domain.User{
		Email:        req.Email,
		PasswordHash: hashed,
		Name:         req.Name,
		Role:         domain.UserRole(req.Role),
	}

	if err := s.userRepo.Create(ctx, user); err != nil {
		return nil, fmt.Errorf("failed to create user: %v", err)
	}

	accessToken, refreshToken, expiresIn, err := s.jwtHelper.GenerateTokenPair(user)
	if err != nil {
		return nil, fmt.Errorf("failed to generate tokens: %v", err)
	}

	session := &domain.Session{
		UserID:       user.ID,
		RefreshToken: refreshToken,
		ExpiresAt:    time.Now().Add(time.Duration(expiresIn) * time.Second),
	}

	if err := s.sessionRepo.Create(ctx, session); err != nil {
		return nil, fmt.Errorf("failed to create session: %v", err)
	}

	return &dto.AuthResponse{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		ExpiresIn:    expiresIn,
		User: dto.UserResponse{
			ID:        user.ID.String(),
			Email:     user.Email,
			Name:      user.Name,
			Role:      string(user.Role),
			CreatedAt: user.CreatedAt,
			UpdatedAt: user.UpdatedAt,
		},
	}, nil
}

// ✅ Login
func (s *authService) Login(ctx context.Context, req *dto.LoginRequest) (*dto.AuthResponse, error) {
	user, err := s.userRepo.FindByEmail(ctx, req.Email)
	if err != nil {
		return nil, fmt.Errorf("invalid email or password")
	}

	if !s.jwtHelper.CheckPasswordHash(req.Password, user.PasswordHash) {
		return nil, fmt.Errorf("invalid email or password")
	}

	accessToken, refreshToken, expiresIn, err := s.jwtHelper.GenerateTokenPair(user)
	if err != nil {
		return nil, fmt.Errorf("failed to generate tokens: %v", err)
	}

	session := &domain.Session{
		UserID:       user.ID,
		RefreshToken: refreshToken,
		ExpiresAt:    time.Now().Add(time.Duration(expiresIn) * time.Second),
	}

	if err := s.sessionRepo.Create(ctx, session); err != nil {
		return nil, fmt.Errorf("failed to create session: %v", err)
	}

	return &dto.AuthResponse{
		AccessToken:  accessToken,
		RefreshToken: refreshToken,
		ExpiresIn:    expiresIn,
		User: dto.UserResponse{
			ID:        user.ID.String(),
			Email:     user.Email,
			Name:      user.Name,
			Role:      string(user.Role),
			CreatedAt: user.CreatedAt,
			UpdatedAt: user.UpdatedAt,
		},
	}, nil
}

// ✅ RefreshToken
func (s *authService) RefreshToken(ctx context.Context, refreshToken string) (*dto.AuthResponse, error) {
	session, err := s.sessionRepo.FindByRefreshToken(ctx, refreshToken)
	if err != nil {
		return nil, fmt.Errorf("invalid or expired refresh token")
	}
	user, err := s.userRepo.FindByID(ctx, session.UserID)
	if err != nil {
		return nil, fmt.Errorf("user not found")
	}

	accessToken, newRefreshToken, expiresIn, err := s.jwtHelper.GenerateTokenPair(user)
	if err != nil {
		return nil, fmt.Errorf("failed to generate tokens: %v", err)
	}

	session.RefreshToken = newRefreshToken
	session.ExpiresAt = time.Now().Add(time.Duration(expiresIn) * time.Second)
	if err := s.sessionRepo.Update(ctx, session); err != nil {
		return nil, fmt.Errorf("failed to update session: %v", err)
	}

	return &dto.AuthResponse{
		AccessToken:  accessToken,
		RefreshToken: newRefreshToken,
		ExpiresIn:    expiresIn,
		User: dto.UserResponse{
			ID:    user.ID.String(),
			Email: user.Email,
			Name:  user.Name,
			Role:  string(user.Role),
		},
	}, nil
}

// ✅ Logout
func (s *authService) Logout(ctx context.Context, userID string, sessionID string) error {
	return s.sessionRepo.DeleteByUserID(ctx, uuid.MustParse(userID))
}

// ✅ ChangePassword
func (s *authService) ChangePassword(ctx context.Context, userID string, req *dto.ChangePasswordRequest) error {
	id := uuid.MustParse(userID)
	user, err := s.userRepo.FindByID(ctx, id)
	if err != nil {
		return fmt.Errorf("user not found")
	}
	if !s.jwtHelper.CheckPasswordHash(req.OldPassword, user.PasswordHash) {
		return fmt.Errorf("incorrect old password")
	}
	newHash, err := s.jwtHelper.HashPassword(req.NewPassword)
	if err != nil {
		return fmt.Errorf("failed to hash password: %v", err)
	}
	user.PasswordHash = newHash
	return s.userRepo.Update(ctx, user)
}
