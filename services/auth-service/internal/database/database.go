package database

import (
	"fmt"
	"os"

	"github.com/joho/godotenv"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/domain"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// NewDatabase initializes a GORM DB connection using DATABASE_URL or components from env.
// It tries to load .env if present. Returns (*gorm.DB, error).
func NewDatabase() (*gorm.DB, error) {
	_ = godotenv.Load() // ignore error; env may be set externally

	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		// try to assemble DSN from parts (Postgres)
		host := os.Getenv("DB_HOST")
		port := os.Getenv("DB_PORT")
		user := os.Getenv("DB_USER")
		password := os.Getenv("DB_PASSWORD")
		dbname := os.Getenv("DB_NAME")
		sslmode := os.Getenv("DB_SSLMODE")
		if sslmode == "" {
			sslmode = "disable"
		}
		if host == "" || port == "" || user == "" || dbname == "" {
			return nil, fmt.Errorf("database configuration not found in environment")
		}
		dsn = fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=%s", host, port, user, password, dbname, sslmode)
	}

	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		return nil, err
	}
	return db, nil
}
func RunMigrations(db *gorm.DB) error {
	return db.AutoMigrate(
		&domain.User{},
		&domain.Session{},
		&domain.Account{},
	)
}
