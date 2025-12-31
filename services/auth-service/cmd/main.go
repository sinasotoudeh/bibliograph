// cmd/main.go
package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/sinas/bibliograph-ai/services/auth-service/config"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/handler"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/repository"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/router"
	"github.com/sinas/bibliograph-ai/services/auth-service/internal/service"
	"github.com/sinas/bibliograph-ai/services/auth-service/pkg/database"
	"github.com/sinas/bibliograph-ai/services/auth-service/pkg/logger"

	"github.com/go-playground/validator/v10"
    "github.com/joho/godotenv"
	"go.uber.org/zap"
)

func main() {
    // Load .env file
    if err := godotenv.Load(); err != nil {
        fmt.Println("Warning: .env file not found or failed to load")
    }
	// Initialize logger
	log, err := logger.InitLogger(logger.InfoLevel)
	if err != nil {
		fmt.Printf("Failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer log.Sync()

	// Load configuration
	cfg, err := config.LoadConfig()
	if err != nil {
		log.Fatal("Failed to load config", zap.Error(err))
	}

	log.Info("Starting Auth Service", zap.String("env", cfg.Server.Env))

	// Connect to database
	db, err := database.Connect(&cfg.Database)
	if err != nil {
		log.Fatal("Failed to connect to database", zap.Error(err))
	}

	log.Info("Database connected successfully")

	// Run migrations
	if err := database.RunMigrations(db); err != nil {
		log.Fatal("Failed to run migrations", zap.Error(err))
	}

	log.Info("Database migrations completed")

	// Initialize repositories
	userRepo := repository.NewUserRepository(db)
	sessionRepo := repository.NewSessionRepository(db)

	// Initialize JWT helper
	jwtHelper := service.NewJWTHelper(cfg)

	// Initialize services
	authService := service.NewAuthService(userRepo, sessionRepo, jwtHelper)
	userService := service.NewUserService(userRepo, sessionRepo)

	// Initialize validator
	validate := validator.New()

	// Initialize handlers
	authHandler := handler.NewAuthHandler(authService, validate)
	userHandler := handler.NewUserHandler(userService, validate)
	healthHandler := handler.NewHealthHandler()

	// Setup router (pass health handler and jwt validator)
	r := router.NewRouter(authHandler, userHandler, healthHandler, jwtHelper)

	// Create server
	addr := fmt.Sprintf("%s:%s", cfg.Server.Host, cfg.Server.Port)
	srv := &http.Server{
		Addr:         addr,
		Handler:      r,
		ReadTimeout:  cfg.Server.ReadTimeout,
		WriteTimeout: cfg.Server.WriteTimeout,
	}

	// Start server in goroutine
	go func() {
		log.Info("Server starting", zap.String("address", addr))
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal("Server failed to start", zap.Error(err))
		}
	}()

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Info("Server shutting down...")

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal("Server forced to shutdown", zap.Error(err))
	}

	// Close database connection
	if err := database.Close(); err != nil {
		log.Error("Error closing database", zap.Error(err))
	}

	log.Info("Server stopped gracefully")
}
