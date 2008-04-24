/* Drobo Utils Copyright (C) 2008  Peter Silva (Peter.A.Silva@gmail.com)
 * Drobo Utils comes with ABSOLUTELY NO WARRANTY; For details type see the file
 * named COPYING in the root of the source directory tree. (GPLv3)
 *   
 * What is DroboDMP.c?
 * DroboDMP.c  is a small python extension to perform the ioctl which is painful 
 * to do in python.  That's all this layer is for.  All the rest of the smarts 
 * are in the python Drobo class.  For example, this layer should be portable
 * because all the byte ordering was pushed up to python, where it's easier.
 *
 * FIXME: get rid of this C-extension: 
 *   anybody know how to call an ioctl from python with pointers to structs in it?
 *
 * Credits:
 *
 * I guess this file is a compatibly sub-licensed derived work?
 * dunno if needs something particular to deal with this...  whatever...
 *
 * This code is heavily based on sample code from Data Robotics Inc...
 * which is in turn based on code in sg_simple1 from sg3_utils and which is:
 *
 *  Copyright (C) 1999-2007 D. Gilbert
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2, or (at your option)
 *  any later version.
 */

#include <Python.h>

#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <scsi/sg_lib.h>
#include <scsi/sg_io_linux.h>

#define DEBUG (1)

/* FIXME: this is crap... I did not want to bother with a full python 
 * object, so I settled for a couple global variables.
 * this means that a single process can only have a single drobo_fd open at once.
 */
static int drobo_fd = -1;
static int debug = 0;

signed int put_mode_page(int sg_fd, void *page_struct, int size, 
    void*mcb, int mcblen, int out, long debug)
/* return the number of bytes placed in the sense buffer */
{
    unsigned char sense_buffer[32];
    sg_io_hdr_t io_hdr;
    int i;
    unsigned char c;

    /* Prepare MODE command */
    memset(&io_hdr, 0, sizeof(sg_io_hdr_t));
 
    if (debug) {
      fprintf( stderr, "\nCDB DUMP START:" );
      for (i=0; i < mcblen; i++) {
         if ((i%8)==0) fprintf(stderr, "\nCDB[%3d] ", i );
         c= *((char*)(mcb+i));
         fprintf(stderr, " 0x%02x", c );
      };
      fprintf(stderr,"\nCDB DUMP COMPLETE\n");
    };

    io_hdr.interface_id = 'S';
    io_hdr.dxfer_direction = SG_DXFER_TO_DEV;
    io_hdr.cmd_len = mcblen;
    io_hdr.mx_sb_len = sizeof(sense_buffer);
    io_hdr.dxfer_len = size;
    io_hdr.dxferp = page_struct;
    io_hdr.cmdp = mcb;
    io_hdr.sbp = sense_buffer;
    io_hdr.timeout = 20000;     /* 20000 millisecs == 20 seconds */
    
    /* these are set by the ioctl... initializing just in case. */
    io_hdr.sb_len_wr=0;   
    io_hdr.resid=0;
    io_hdr.status=99;  

    i=ioctl(sg_fd, SG_IO, &io_hdr);
    if (i < 0) {
        perror("Drobo put_mode_page SG_IO ioctl error");
        close(sg_fd);
        return(-1);
    }

    if (debug) fprintf(stderr, 
        "\nread.. size=%d, io_hdr: status=%d, sb_len_wr=%d, resid=%d, \n", 
          size, io_hdr.status, io_hdr.sb_len_wr, io_hdr.resid );

    /* SG_INFO_DIRECT_IO       0x2     -- direct IO requested and performed */
    if ((io_hdr.status != 0) && (io_hdr.status != 2)) {
       fprintf( stderr, "oh no! io_hdr status is: %d\n",  io_hdr.status );
       return(-1);
    } else {
      if (io_hdr.resid > 0) {
        size -= io_hdr.resid   ;
      }
    }

    return(size);
}

signed int get_mode_page(int sg_fd, void *page_struct, int size, 
    void*mcb, int mcblen, int out, long debug)
/* return the number of bytes placed in the sense buffer */
{
    unsigned char sense_buffer[32];
    sg_io_hdr_t io_hdr;
    int i;
    unsigned char c;

    /* Prepare MODE command */
    memset(&io_hdr, 0, sizeof(sg_io_hdr_t));
 
    if (debug) {
      fprintf( stderr, "\nCDB DUMP START:" );
      for (i=0; i < mcblen; i++) {
         if ((i%8)==0) fprintf(stderr, "\nCDB[%3d] ", i );
         c= *((char*)(mcb+i));
         fprintf(stderr, " 0x%02x", c );
      };
      fprintf(stderr,"\nCDB DUMP COMPLETE\n");
    };

    io_hdr.interface_id = 'S';
    io_hdr.dxfer_direction = (out) ? SG_DXFER_TO_DEV : SG_DXFER_FROM_DEV;
    io_hdr.cmd_len = mcblen;
    io_hdr.mx_sb_len = sizeof(sense_buffer);
    io_hdr.dxfer_len = size;
    io_hdr.dxferp = page_struct;
    io_hdr.cmdp = mcb;
    io_hdr.sbp = sense_buffer;
    io_hdr.timeout = 20000;     /* 20000 millisecs == 20 seconds */
    
    /* these are set by the ioctl... initializing just in case. */
    io_hdr.sb_len_wr=0;   
    io_hdr.resid=0;
    io_hdr.status=99;  

    i=ioctl(sg_fd, SG_IO, &io_hdr);
    if (i < 0) {
        perror("Drobo get_mode_page SG_IO ioctl error");
        close(sg_fd);
        return(-1);
    }

    if (debug) fprintf(stderr, 
        "\nread.. size=%d, io_hdr: status=%d, sb_len_wr=%d, resid=%d, \n", 
          size, io_hdr.status, io_hdr.sb_len_wr, io_hdr.resid );

    /* SG_INFO_DIRECT_IO       0x2     -- direct IO requested and performed */
    if ((io_hdr.status != 0) && (io_hdr.status != 2)) {
       fprintf( stderr, "oh no! io_hdr status is: %d\n",  io_hdr.status );
       return(-1);
    } else {
      if (io_hdr.resid > 0) {
        size -= io_hdr.resid   ;
      }
    }

    return(size);

}

PyObject *drobodmp_put_sub_page( PyObject* self, PyObject* args ) {
    char * buffer = NULL;
    long buflen;
    int i;
    char c;
    unsigned char * mcb = NULL;
    long mcblen;
    long debug =0;

    // parse arguments... 
    fprintf(stderr, "put_sub_page 1\n");

    if (!PyArg_ParseTuple(args, "s#s#l", &mcb, &mcblen, &buffer, &buflen, &debug )){
        PyErr_SetString( PyExc_ValueError, 
	  "requires 3 arguments: mcb, sensebuffer, debug" );
        return(NULL);
    }

    if (debug) {
         fprintf( stderr, "\nSB DUMP START:" );
         for (i=0; i < buflen; i++) {
            if ((i%8)==0) fprintf(stderr, "\nSB[%3d] ", i );
            c= *((char*)(buffer+i));
            fprintf(stderr, " 0x%02x", c );
         };
         fprintf(stderr,"\nSB DUMP COMPLETE\n");
    };
 

    if (debug) fprintf(stderr, "put_sub_page 2\n");

    put_mode_page(drobo_fd, buffer, buflen, mcb, mcblen, 1, debug);

    if (debug) fprintf(stderr, "put_sub_page 3\n");
  
    return(Py_BuildValue("i", 0));
};


PyObject *drobodmp_get_sub_page( PyObject* self, PyObject* args ) {

/*  Perform ioctl to retrieve a sub-page from the Drobo.
 *    required arguments:
 *           sz   : length of buffer to be returned.
 *                  if the ioctl indicates a residual amount
 *           mcb  : some scsi control block thingum...
 *                  pass transparently through to ioctl/SG
 *           out  : choose direction of xfer.  out= to device.
 *           debug : if 1,then print debugging output (lots of it.)
 */

    char * buffer = NULL;
    long sz = 0 ;
    long out = 0;
    long  szwritten = 0;
    unsigned char * mcb = NULL;
    long mcblen;
    PyObject *retval;
    PyObject *empty_tuple;
    long debug =0;

    // parse arguments... 
    if (drobo_fd < 0) {
        PyErr_SetString( PyExc_ValueError, "no open drobo.  Call open first" );
        return(NULL);
    }
    if (!PyArg_ParseTuple(args, "ls#ll", &sz, &mcb, &mcblen, &out, &debug )){
        PyErr_SetString( PyExc_ValueError, 
	  "requires 5 arguments: length, mcb, out-boolean, debug" );
        return(NULL);
    }

    if (debug) fprintf(stderr, "get_sub_page 2\n");

    empty_tuple=PyTuple_New(0);

    if (debug) fprintf(stderr, "get_sub_page 3\n");

    buffer = PyMem_Malloc(sz);
    if (buffer == NULL)  {
          PyErr_SetString( PyExc_RuntimeError, "failed to allocate read buffer");
    }
    bzero(buffer,sz);
 
    if (debug) fprintf(stderr, "get_sub_page 4\n");

    szwritten = get_mode_page(drobo_fd, buffer, sz, mcb, mcblen, out, debug);

    if (debug) fprintf(stderr, "get_sub_page 5\n");

    if (szwritten > 0)  {
         retval = PyString_FromStringAndSize(buffer, szwritten );
    } else {
         retval = NULL;
         PyMem_Free(buffer);
    }

    if (debug) fprintf(stderr, "get_sub_page 6\n");


    return(retval);
};


PyObject *drobodmp_openfd( PyObject* self, PyObject* args ) {
    char *file_name = NULL;
    int readwrite;
    int k;

    if (!PyArg_ParseTuple(args, "sll", &file_name, &readwrite, &debug )){
        PyErr_SetString( PyExc_ValueError, 
	  "requires 3 arguments: filename, rwflag, debugflag.  rwflag=0 --> rdonly " );
        return(NULL);
    }
    if (debug) fprintf( stderr, "openfd/open %s, \n", file_name );

    if ((drobo_fd = open(file_name, readwrite?O_RDWR:O_RDONLY)) < 0) {
        PyErr_SetFromErrnoWithFilename( PyExc_OSError, file_name );
        return(NULL);
    }

    if (debug) fprintf( stderr, "openfd/ioctl %s, \n", file_name );

    /* Just to be safe, check we have a new sg device by trying an ioctl */
    if ((ioctl(drobo_fd, SG_GET_VERSION_NUM, &k) < 0) || (k < 30000)) {
        PyErr_SetFromErrnoWithFilename( PyExc_OSError, file_name );
        close(drobo_fd);
        drobo_fd=-1;
        return(NULL);
    }
    if (debug) fprintf( stderr, "openfd/ioctl %s, worked...\n", file_name );

   return(Py_BuildValue("i", drobo_fd));
}

PyObject *drobodmp_closefd( PyObject* self, PyObject* args ) {

   if (drobo_fd >= 0) close(drobo_fd);
   drobo_fd=-1;
   return(Py_BuildValue("i", 0));
}

static PyMethodDef DroboDMPMethods[] = {
    { "get_sub_page", drobodmp_get_sub_page, METH_VARARGS|METH_KEYWORDS, 
                  "retrieve a Drobo Management Protocol formatted scsi control block" },
    { "put_sub_page", drobodmp_get_sub_page, METH_VARARGS|METH_KEYWORDS, 
                  "set a Drobo Management Protocol formatted scsi control block" },
    { "openfd", drobodmp_openfd, METH_VARARGS|METH_KEYWORDS, 
                  "open drobo file descriptor" },
    { "closefd", drobodmp_closefd, METH_VARARGS|METH_KEYWORDS, 
                  "close drobo file descriptor" },
    { NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC initDroboDMP(void) {

  (void) Py_InitModule("DroboDMP", DroboDMPMethods );
}

