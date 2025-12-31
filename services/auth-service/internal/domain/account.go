package domain

import (
	"time"

	"github.com/google/uuid"
)

type OAuthProvider string

const (
	OAuthProviderGoogle OAuthProvider = "google"
	OAuthProviderGithub OAuthProvider = "github"
)

type Account struct {
	ID            uuid.UUID     `gorm:"type:uuid;primary_key;default:gen_random_uuid()" json:"id"`
	UserID        uuid.UUID     `gorm:"type:uuid;not null;index" json:"user_id"`
	Provider      OAuthProvider `gorm:"type:varchar(50);not null" json:"provider"`
	ProviderID    string        `gorm:"type:varchar(255);not null" json:"provider_id"`
	AccessToken   string        `gorm:"type:text" json:"-"`
	RefreshToken  string        `gorm:"type:text" json:"-"`
	ExpiresAt     *time.Time    `gorm:"type:timestamp" json:"expires_at,omitempty"`
	TokenType     string        `gorm:"type:varchar(50)" json:"token_type,omitempty"`
	Scope         string        `gorm:"type:varchar(500)" json:"scope,omitempty"`
	Email         string        `gorm:"type:varchar(255)" json:"email,omitempty"`
	EmailVerified bool          `gorm:"default:false" json:"email_verified"`
	CreatedAt     time.Time     `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt     time.Time     `gorm:"autoUpdateTime" json:"updated_at"`

	// Relations
	User User `gorm:"foreignKey:UserID;constraint:OnUpdate:CASCADE,OnDelete:CASCADE" json:"user,omitempty"`
}

func (Account) TableName() string {
	return "oauth_accounts"
}

