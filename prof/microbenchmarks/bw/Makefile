CC     = gcc
CFLAGS = -I. -W -Wall -Wextra -Wuninitialized -Wstrict-aliasing -march=native -O3
LDLIBS = -lpthread -lnuma -lm
DEPS   = utils.h
OBJ    = utils.o main.o

.PHONY: all clean

all: bw

%.o: %.c $(DEPS)
	$(CC) -c -o $@ $< $(CFLAGS)

bw: $(OBJ)
	$(CC) -o $@ $^ $(CFLAGS) $(LDLIBS)

clean:
	$(RM) *~ *.o bw
