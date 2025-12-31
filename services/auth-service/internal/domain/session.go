package domain

import (
	"time"

	"github.com/google/uuid"
)

type Session struct {
	ID           uuid.UUID `gorm:"type:uuid;primary_key;default:gen_random_uuid()" json:"id"`
	UserID       uuid.UUID `gorm:"type:uuid;not null;index" json:"user_id"`
	RefreshToken string    `gorm:"type:text;unique;not null" json:"refresh_token"`
	UserAgent    string    `gorm:"type:varchar(500)" json:"user_agent,omitempty"`
	IPAddress    string    `gorm:"type:varchar(45)" json:"ip_address,omitempty"`
	ExpiresAt    time.Time `gorm:"type:timestamp;not null" json:"expires_at"`
	CreatedAt    time.Time `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt    time.Time `gorm:"autoUpdateTime" json:"updated_at"`

	// Relations
	User User `gorm:"foreignKey:UserID;constraint:OnUpdate:CASCADE,OnDelete:CASCADE" json:"user,omitempty"`
}

func (Session) TableName() string {
	return "sessions"
}
