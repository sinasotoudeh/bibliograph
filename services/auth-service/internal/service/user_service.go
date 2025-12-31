package service

import (
	"context"

	"github.com/google/uuid"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/domain"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/dto"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/repository"
)

// userService implements UserService interface
type userService struct {
	userRepo    repository.UserRepository
	sessionRepo repository.SessionRepository
}

// NewUserService creates a new UserService
func NewUserService(userRepo repository.UserRepository, sessionRepo repository.SessionRepository) UserService {
	return &userService{
		userRepo:    userRepo,
		sessionRepo: sessionRepo,
	}
}

// GetUserByID looks up a user by UUID string
func (s *userService) GetUserByID(ctx context.Context, userID string) (*domain.User, error) {
	id, err := uuid.Parse(userID)
	if err != nil {
		return nil, err
	}
	return s.userRepo.FindByID(ctx, id)
}

// UpdateUser updates allowed fields of a user based on UpdateUserRequest
func (s *userService) UpdateUser(ctx context.Context, userID string, req *dto.UpdateUserRequest) error {
	id, err := uuid.Parse(userID)
	if err != nil {
		return err
	}
	u, err := s.userRepo.FindByID(ctx, id)
	if err != nil {
		return err
	}
	// apply updateable fields if provided
	if req.Email != nil {
		u.Email = *req.Email
	}
	if req.Name != nil {
		u.Name = *req.Name
	}
	if req.Role != nil {
		// convert string to domain.UserRole
		u.Role = domain.UserRole(*req.Role)
	}
	return s.userRepo.Update(ctx, u)
}

// DeleteUser deletes user by id
func (s *userService) DeleteUser(ctx context.Context, userID string) error {
	id, err := uuid.Parse(userID)
	if err != nil {
		return err
	}
	return s.userRepo.Delete(ctx, id)
}
