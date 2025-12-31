package service

import (
	"errors"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"golang.org/x/crypto/bcrypt"

	"github.com/sinas/bibliograph-ai/services/auth-service/config"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/domain"
)

// JWTHelper اینترفیس واقعی مورد استفاده در AuthService
type JWTHelper interface {
	HashPassword(password string) (string, error)
	CheckPasswordHash(password, hash string) bool
	GenerateTokenPair(user *domain.User) (string, string, int64, error)
	ValidateToken(tokenString string) (*domain.Claims, error)
}

// jwtHelper پیاده‌سازی واقعی JWTHelper
type jwtHelper struct {
	secret        []byte
	issuer        string
	accessExpiry  time.Duration
	refreshExpiry time.Duration
}

// سازنده JWTHelper با config سرویس
func NewJWTHelper(cfg *config.Config) JWTHelper {
	return &jwtHelper{
		secret:        []byte(cfg.JWT.Secret),
		issuer:        cfg.JWT.Issuer,
		accessExpiry:  cfg.JWT.AccessExpiry,
		refreshExpiry: cfg.JWT.RefreshExpiry,
	}
}

// ✅ هش کردن رمز عبور
func (h *jwtHelper) HashPassword(password string) (string, error) {
	bytes, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	return string(bytes), err
}

// ✅ بررسی صحت رمز هش‌شده
func (h *jwtHelper) CheckPasswordHash(password, hash string) bool {
	return bcrypt.CompareHashAndPassword([]byte(hash), []byte(password)) == nil
}

// ✅ تولید توکن جفت (Access + Refresh)
func (h *jwtHelper) GenerateTokenPair(user *domain.User) (accessToken, refreshToken string, expiresIn int64, err error) {
	now := time.Now()
	expiresIn = int64(h.accessExpiry.Seconds())

	accessClaims := &domain.Claims{
		UserID:           user.ID,
		Email:            user.Email,
		Role:             user.Role,
		SubscriptionTier: user.SubscriptionTier,
		IssuedAt:         now,
		ExpiresAt:        now.Add(h.accessExpiry),
		RegisteredClaims: jwt.RegisteredClaims{
			Issuer:    h.issuer,
			IssuedAt:  jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.Add(h.accessExpiry)),
			Subject:   uuid.NewString(),
		},
	}

	refreshClaims := &domain.Claims{
		UserID:           user.ID,
		Email:            user.Email,
		Role:             user.Role,
		SubscriptionTier: user.SubscriptionTier,
		IssuedAt:         now,
		ExpiresAt:        now.Add(h.refreshExpiry),
		RegisteredClaims: jwt.RegisteredClaims{
			Issuer:    h.issuer,
			IssuedAt:  jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.Add(h.refreshExpiry)),
			Subject:   uuid.NewString(),
		},
	}

	accessToken, err = jwt.NewWithClaims(jwt.SigningMethodHS256, accessClaims).SignedString(h.secret)
	if err != nil {
		return "", "", 0, err
	}

	refreshToken, err = jwt.NewWithClaims(jwt.SigningMethodHS256, refreshClaims).SignedString(h.secret)
	if err != nil {
		return "", "", 0, err
	}

	return accessToken, refreshToken, expiresIn, nil
}

// ✅ اعتبارسنجی توکن JWT
func (h *jwtHelper) ValidateToken(tokenString string) (*domain.Claims, error) {
	token, err := jwt.ParseWithClaims(tokenString, &domain.Claims{}, func(t *jwt.Token) (interface{}, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, errors.New("unexpected signing method")
		}
		return h.secret, nil
	})
	if err != nil {
		return nil, err
	}
	if !token.Valid {
		return nil, errors.New("invalid token")
	}

	claims, ok := token.Claims.(*domain.Claims)
	if !ok {
		return nil, errors.New("invalid claims structure")
	}

	return claims, nil
}
