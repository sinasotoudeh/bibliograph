// internal/domain/user.go
package domain

import (
	"time"

	"github.com/google/uuid"
)

type UserRole string

const (
	UserRoleAdmin      UserRole = "admin"
	UserRoleResearcher UserRole = "researcher"
	UserRoleTranslator UserRole = "translator"
	UserRolePublisher  UserRole = "publisher"
	UserRoleStudent    UserRole = "student"
)

type SubscriptionTier string

const (
	SubscriptionTierFree     SubscriptionTier = "free"
	SubscriptionTierBasic    SubscriptionTier = "basic"
	SubscriptionTierPremium  SubscriptionTier = "premium"
	SubscriptionTierResearch SubscriptionTier = "research"
)

type User struct {
	ID                uuid.UUID        `gorm:"type:uuid;primary_key;default:gen_random_uuid()" json:"id"`
	Name              string           `gorm:"type:varchar(255);not null" json:"name"`
	Email             string           `gorm:"type:varchar(255);unique;not null" json:"email"`
	PasswordHash      string           `gorm:"type:varchar(255);not null" json:"-"`
	Role              UserRole         `gorm:"type:varchar(50);default:'student'" json:"role"`
	SubscriptionTier  SubscriptionTier `gorm:"type:varchar(50);default:'free'" json:"subscription_tier"`
	Bio               *string          `gorm:"type:text" json:"bio,omitempty"`
	Avatar            *string          `gorm:"type:varchar(500)" json:"avatar,omitempty"`
	Institution       *string          `gorm:"type:varchar(255)" json:"institution,omitempty"`
	PhoneNumber       *string          `gorm:"type:varchar(50)" json:"phone_number,omitempty"`
	Interests         []string         `gorm:"type:text[]" json:"interests,omitempty"`
	EmailVerified     bool             `gorm:"default:false" json:"email_verified"`
	EmailVerifiedAt   *time.Time       `gorm:"type:timestamp" json:"email_verified_at,omitempty"`
	SearchesThisMonth int              `gorm:"default:0" json:"searches_this_month"`
	ExportsThisMonth  int              `gorm:"default:0" json:"exports_this_month"`
	LastLoginAt       *time.Time       `gorm:"type:timestamp" json:"last_login_at,omitempty"`
	CreatedAt         time.Time        `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt         time.Time        `gorm:"autoUpdateTime" json:"updated_at"`
}

func (User) TableName() string {
	return "users"
}
