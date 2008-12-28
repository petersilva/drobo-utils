
#include <stdio.h>

int main(int argc, char *argv[]) {

  int ch, x, key;
  FILE *input = fopen( argv[1], "r" );             

   ch = getc( input );
   key = ch ^ 0x2d ;
   while( ch != EOF ) {
     x = ch^key;
     printf( "%c", x );
     ch = getc( input );
   }     
}
