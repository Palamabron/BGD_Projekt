#!/bin/bash
# Skrypt do uruchomienia całego pipeline'u i przetestowania go
# z opcją resetowania całego środowiska

# Kolory do formatowania wyjścia
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Domyślne wartości dla opcji
RESET_ENV=false
DEBUG_MODE=false
SKIP_TEST=false

# Funkcja wyświetlająca użycie skryptu
show_usage() {
  echo -e "${YELLOW}Użycie: $0 [opcje]${NC}"
  echo -e "Opcje:"
  echo -e "  -r, --reset     Resetuj całe środowisko (usuwa wszystkie woluminy i dane)"
  echo -e "  -d, --debug     Uruchom w trybie debugowania (więcej logów)"
  echo -e "  -s, --skip-test Pomiń uruchomienie testu pipeline'u"
  echo -e "  -h, --help      Wyświetl tę pomoc"
  exit 1
}

# Przetwarzanie opcji wiersza poleceń
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -r|--reset)
      RESET_ENV=true
      shift
      ;;
    -d|--debug)
      DEBUG_MODE=true
      shift
      ;;
    -s|--skip-test)
      SKIP_TEST=true
      shift
      ;;
    -h|--help)
      show_usage
      ;;
    *)
      echo -e "${RED}Nieznana opcja: $1${NC}"
      show_usage
      ;;
  esac
done

# Funkcja do wyświetlania komunikatów statusu
log() {
  echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Funkcja do wyświetlania komunikatów debugowania
debug() {
  if [ "$DEBUG_MODE" = true ]; then
    echo -e "${YELLOW}[DEBUG][$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
  fi
}

# Funkcja do wyświetlania komunikatów sukcesu
success() {
  echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Funkcja do wyświetlania ostrzeżeń
warning() {
  echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Funkcja do wyświetlania błędów
error() {
  echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Główny nagłówek
echo -e "\n${YELLOW}==========================================${NC}"
echo -e "${YELLOW}  URUCHAMIANIE I TESTOWANIE PIPELINE'U    ${NC}"
echo -e "${YELLOW}==========================================${NC}\n"

# Jeśli wybrano opcję resetowania, uruchom skrypt reset-environment.sh
if [ "$RESET_ENV" = true ]; then
  log "Rozpoczynam resetowanie całego środowiska..."
  
  # Sprawdź, czy skrypt reset-environment.sh istnieje
  if [ ! -f "./reset-environment.sh" ]; then
    error "Skrypt reset-environment.sh nie istnieje!"
    exit 1
  fi
  
  # Sprawdź, czy skrypt ma uprawnienia do wykonania
  if [ ! -x "./reset-environment.sh" ]; then
    warning "Skrypt reset-environment.sh nie ma uprawnień do wykonania. Nadaję uprawnienia..."
    chmod +x ./reset-environment.sh
  fi
  
  debug "Wykonuję skrypt resetowania środowiska"
  ./reset-environment.sh
  
  if [ $? -ne 0 ]; then
    error "Resetowanie środowiska zakończyło się błędem!"
    exit 1
  fi
  
  success "Środowisko zostało zresetowane pomyślnie!"
else
  # Regularne uruchamianie bez resetowania
  log "Uruchamianie pipeline'u bez resetowania środowiska..."
  
  # 1. Zatrzymanie wszystkich kontenerów
  log "Zatrzymywanie wszystkich kontenerów..."
  docker-compose down
  
  # 2. Uruchamianie kontenerów w określonej kolejności
  log "Rozpoczynam uruchamianie kontenerów w określonej kolejności..."
  
  # Zookeeper
  log "Uruchamianie Zookeeper..."
  docker-compose up -d zookeeper
  sleep 10
  
  # Kafka
  log "Uruchamianie Kafka..."
  docker-compose up -d kafka
  sleep 20
  
  # PostgreSQL
  log "Uruchamianie PostgreSQL..."
  docker-compose up -d postgres_db
  sleep 15
  
  # MinIO
  log "Uruchamianie MinIO..."
  docker-compose up -d minio
  sleep 10
  
  # Spark Master
  log "Uruchamianie Spark Master..."
  docker-compose up -d spark-master
  sleep 15
  
  # Spark Worker
  log "Uruchamianie Spark Worker..."
  docker-compose up -d spark-worker
  sleep 15
  
  # Debezium
  log "Uruchamianie Debezium..."
  docker-compose up -d debezium
  sleep 30
  
  # Spark App
  log "Uruchamianie aplikacji Spark..."
  docker-compose up -d spark-app
  sleep 20
fi

# 3. Sprawdzanie stanu wszystkich kontenerów
echo -e "\n${YELLOW}==========================================${NC}"
echo -e "${YELLOW}             STAN KONTENERÓW             ${NC}"
echo -e "${YELLOW}==========================================${NC}\n"

log "Sprawdzanie stanu wszystkich kontenerów..."
docker-compose ps

# 4. Uruchamianie skryptu testowego pipeline'u (jeśli nie pominięto)
if [ "$SKIP_TEST" = false ]; then
  echo -e "\n${YELLOW}==========================================${NC}"
  echo -e "${YELLOW}          TESTOWANIE PIPELINE'U           ${NC}"
  echo -e "${YELLOW}==========================================${NC}\n"
  
  log "Uruchamianie testu pipeline'u..."
  log "Wykonuję: ./test_pipeline.sh"
  echo
  
  # Sprawdzenie, czy skrypt test_pipeline.sh istnieje i ma uprawnienia do wykonania
  if [ ! -f "./test_pipeline.sh" ]; then
    error "Skrypt test_pipeline.sh nie istnieje!"
    exit 1
  fi
  
  if [ ! -x "./test_pipeline.sh" ]; then
    warning "Skrypt test_pipeline.sh nie ma uprawnień do wykonania. Nadaję uprawnienia..."
    chmod +x ./test_pipeline.sh
  fi
  
  # Uruchomienie skryptu testowego
  ./test_pipeline.sh
  
  # Sprawdzenie wyniku testu
  test_result=$?
  echo
  
  if [ $test_result -eq 0 ]; then
    success "Test pipeline'u zakończony sukcesem! 🎉"
  else
    error "Test pipeline'u zakończony z błędem (kod: $test_result)"
    warning "Sprawdź logi poszczególnych kontenerów, aby zidentyfikować problem"
  fi
  
  # 5. Sprawdzanie, czy dane zostały przetworzane w MinIO
  echo -e "\n${YELLOW}==========================================${NC}"
  echo -e "${YELLOW}       SPRAWDZANIE DANYCH W MINIO         ${NC}"
  echo -e "${YELLOW}==========================================${NC}\n"
  
  log "Sprawdzanie, czy dane zostały zapisane w MinIO..."
  
  # Inicjalizacja MinIO client dla łatwiejszego dostępu
  docker exec minio mc alias set myminio http://localhost:9000 minio minio123 &>/dev/null
  
  # Sprawdzanie bucketów i zawartości
  if docker exec minio mc ls myminio/ | grep -q "processed-data"; then
    success "Bucket 'processed-data' istnieje w MinIO."
    
    log "Sprawdzanie zawartości bucketu 'processed-data'..."
    docker exec minio mc ls myminio/processed-data/ --recursive
    
    # Sprawdzanie katalogów analizy
    if docker exec minio mc ls myminio/processed-data/ | grep -q "klienci-by-country"; then
      success "Katalog 'klienci-by-country' istnieje - analiza klientów została wykonana."
    else
      warning "Katalog 'klienci-by-country' nie istnieje - analiza klientów mogła nie zostać wykonana."
    fi
    
    if docker exec minio mc ls myminio/processed-data/ | grep -q "avg-age-by-position"; then
      success "Katalog 'avg-age-by-position' istnieje - analiza pracowników została wykonana."
    else
      warning "Katalog 'avg-age-by-position' nie istnieje - analiza pracowników mogła nie zostać wykonana."
    fi
    
    if docker exec minio mc ls myminio/processed-data/ | grep -q "raw-kafka-data"; then
      success "Katalog 'raw-kafka-data' istnieje - dane z Kafka zostały zapisane."
    else
      warning "Katalog 'raw-kafka-data' nie istnieje - dane z Kafka mogły nie zostać zapisane."
    fi
  else
    error "Bucket 'processed-data' NIE istnieje w MinIO!"
    warning "Sprawdź logi spark-app, aby zidentyfikować problem"
  fi
else
  log "Pomijam uruchomienie testu pipeline'u (opcja --skip-test)."
fi

# 6. Diagnostyka - opcjonalnie uruchom narzędzie debug_pipeline.py
if [ "$DEBUG_MODE" = true ]; then
  echo -e "\n${YELLOW}==========================================${NC}"
  echo -e "${YELLOW}           DIAGNOSTYKA PIPELINE'U         ${NC}"
  echo -e "${YELLOW}==========================================${NC}\n"
  
  log "Uruchamianie narzędzia diagnostycznego debug_pipeline.py..."
  python debug_pipeline.py
else
  echo -e "\n${YELLOW}==========================================${NC}"
  echo -e "${YELLOW}           DIAGNOSTYKA PIPELINE'U         ${NC}"
  echo -e "${YELLOW}==========================================${NC}\n"
  
  log "Czy chcesz uruchomić narzędzie diagnostyczne debug_pipeline.py? (t/N)"
  read -n 1 -r
  echo
  if [[ $REPLY =~ ^[Tt]$ ]]; then
    log "Uruchamianie narzędzia diagnostycznego..."
    python debug_pipeline.py
  else
    log "Pomijanie uruchomienia narzędzia diagnostycznego."
  fi
fi

# 7. Podsumowanie
echo -e "\n${YELLOW}==========================================${NC}"
echo -e "${YELLOW}               PODSUMOWANIE              ${NC}"
echo -e "${YELLOW}==========================================${NC}\n"

log "Status wszystkich kontenerów:"
docker-compose ps

success "Proces uruchamiania i testowania pipeline'u został zakończony."
log "Jeśli wszystkie kontenery są uruchomione i test nie wykazał błędów, pipeline działa poprawnie."
log "W przypadku problemów, sprawdź logi poszczególnych kontenerów."

# Wskazówki debugowania
echo -e "\n${YELLOW}Przydatne komendy do debugowania:${NC}"
echo -e "${BLUE}docker-compose logs kafka${NC} - Logi Kafka"
echo -e "${BLUE}docker-compose logs debezium${NC} - Logi Debezium"
echo -e "${BLUE}docker-compose logs spark-app${NC} - Logi aplikacji Spark"
echo -e "${BLUE}./start-and-test-pipeline.sh --reset${NC} - Resetowanie całego środowiska"
echo -e "${BLUE}./start-and-test-pipeline.sh --debug${NC} - Uruchomienie w trybie debugowania"
echo -e "${BLUE}python debug_pipeline.py${NC} - Uruchomienie narzędzia diagnostycznego"