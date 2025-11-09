# Makefile for Packet Capture Tool

CC = gcc
CFLAGS = -Wall -Wextra -std=gnu11
LDFLAGS = -lpcap -lpthread

TARGET = capture
SOURCES = capture.c preprocess.c denylist.c rate_limit.c malformed.c
OBJECTS = $(SOURCES:.c=.o)
HEADERS = preprocess.h denylist.h rate_limit.h malformed.h

.PHONY: all clean run test help

all: $(TARGET)

$(TARGET): $(OBJECTS)
	@echo "Linking $(TARGET)..."
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)
	@echo "Build complete: ./$(TARGET)"

%.o: %.c $(HEADERS)
	@echo "Compiling $<..."
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	@echo "Cleaning build artifacts..."
	rm -f $(OBJECTS) $(TARGET)
	@echo "Cleaning output files..."
	rm -f summary_batch_1.csv
	@echo "Clean complete"

run: $(TARGET)
	@echo "Running packet capture (requires sudo)..."
	sudo ./$(TARGET) -n 50

test: $(TARGET)
	@echo "Running test script (requires sudo)..."
	sudo ./test_capture.sh

help:
	@echo "Packet Capture Tool - Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make          - Build the project"
	@echo "  make clean    - Remove build artifacts and output files"
	@echo "  make run      - Build and run (captures 50 packets)"
	@echo "  make test     - Build and run test script"
	@echo "  make help     - Show this help message"
	@echo ""
	@echo "Manual execution:"
	@echo "  sudo ./capture           - Capture from all interfaces"
	@echo "  sudo ./capture -i eth0   - Capture from specific interface"
	@echo "  sudo ./capture -n 100    - Capture N packets"
	@echo ""
	@echo "Configuration files:"
	@echo "  IP.txt    - Blocked IP addresses (one per line)"
	@echo "  Ports.txt - Blocked ports (one per line)"
	@echo ""
	@echo "Output files:"
	@echo "  summary_batch_1.csv - Traffic statistics"
