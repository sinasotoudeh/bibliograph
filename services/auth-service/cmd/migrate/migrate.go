package main

import (
	"log"

	"github.com/sinas/bibliograph-ai/services/auth-service/internal/database"
)

func main() {
	db, err := database.NewDatabase()
	if err != nil {
		log.Fatal(err)
	}
	if err := database.RunMigrations(db); err != nil {
		log.Fatal(err)
	}
	log.Println("✅ Migration done!")
}
