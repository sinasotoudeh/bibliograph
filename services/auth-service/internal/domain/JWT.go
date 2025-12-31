package domain

import (
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

// Claims داخل توکن JWT
type Claims struct {
	UserID           uuid.UUID        `json:"user_id"`
	Email            string           `json:"email"`
	Role             UserRole         `json:"role"`
	SubscriptionTier SubscriptionTier `json:"subscription_tier"`
	IssuedAt         time.Time        `json:"issued_at"`
	ExpiresAt        time.Time        `json:"expires_at"`
	jwt.RegisteredClaims
}

// برای موارد سبک‌تر (اختیاری)
type JWTClaims struct {
	UserID string `json:"user_id"`
	Email  string `json:"email"`
	Role   string `json:"role"`
	jwt.RegisteredClaims
}
