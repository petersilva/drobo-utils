
#include <stdio.h>

/* this works for firmware
 *  1.03 --> 1.1* key= 0xa5
 *  in > 1.2.1 key= 0x2d -- reported to work for Brad Guillory. doesn't for me.
 */

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
