
#include <stdio.h>
int main(int argc, char *argv[]) {

  int ch, x;
  FILE *input = fopen( argv[1], "r" );             

   ch = getc( input );
   while( ch != EOF ) {
     x = ch^0xa5;
     printf( "%c", x );
     ch = getc( input );
   }     
}
