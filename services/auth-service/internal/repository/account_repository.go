package repository

import (
	"context"

	"github.com/google/uuid"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/domain"
	"gorm.io/gorm"
)

type accountRepository struct {
	db *gorm.DB
}

func NewAccountRepository(db *gorm.DB) AccountRepository {
	return &accountRepository{db: db}
}

func (r *accountRepository) Create(ctx context.Context, account *domain.Account) error {
	return r.db.WithContext(ctx).Create(account).Error
}

func (r *accountRepository) FindByID(ctx context.Context, id uuid.UUID) (*domain.Account, error) {
	var account domain.Account
	err := r.db.WithContext(ctx).First(&account, "id = ?", id).Error
	if err != nil {
		return nil, err
	}
	return &account, nil
}

func (r *accountRepository) FindByProviderAndProviderID(ctx context.Context, provider domain.OAuthProvider, providerID string) (*domain.Account, error) {
	var account domain.Account
	err := r.db.WithContext(ctx).
		Where("provider = ? AND provider_account_id = ?", provider, providerID).
		First(&account).Error
	if err != nil {
		return nil, err
	}
	return &account, nil
}

func (r *accountRepository) FindByUserID(ctx context.Context, userID uuid.UUID) ([]*domain.Account, error) {
	var accounts []*domain.Account
	err := r.db.WithContext(ctx).Where("user_id = ?", userID).Find(&accounts).Error
	return accounts, err
}

func (r *accountRepository) Update(ctx context.Context, account *domain.Account) error {
	return r.db.WithContext(ctx).Save(account).Error
}

func (r *accountRepository) Delete(ctx context.Context, id uuid.UUID) error {
	return r.db.WithContext(ctx).Delete(&domain.Account{}, "id = ?", id).Error
}

