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
 * Copyright (C) 1999-2007 D. Gilbert
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

signed int get_mode_page(int sg_fd, void *page_struct, int size, 
    void*mcb, int mcblen, int out)
/* return the number of bytes placed in the sense buffer */
{
    unsigned char sense_buffer[32];
    sg_io_hdr_t io_hdr;
    int i;

    /* Prepare MODE command */
    memset(&io_hdr, 0, sizeof(sg_io_hdr_t));
 
/*    if (DEBUG) {
      fprintf( stderr, "\nCDB dump\n:" );
      for (i=0; i < 11; i++) {
         fprintf(stderr, "CDB[%d] = 0x%02x\n", i, *(char*)(mcb+i) );
      };
    };
 */
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

    fprintf(stderr, 
        "\nread.. size=%d, io_hdr: status=%d, sb_len_wr=%d, resid=%d, \n", 
          size, io_hdr.status, io_hdr.sb_len_wr, io_hdr.resid );

    if (io_hdr.status != 0) {
       fprintf( stderr, "oh no! io_hdr status is: %d\n",  io_hdr.status );
       return(-1);
    } else {
      if (io_hdr.resid > 0) {
        size -= io_hdr.resid   ;
      }
    }

    return(size);

}


PyObject *drobodmp_get_sub_page( PyObject* self, PyObject* args ) {

    int sg_fd, k;
    char * file_name = NULL;
    char * buffer = NULL;
    long sz = 0 ;
    long out = 0;
    long  szwritten = 0;
    unsigned char * mcb = NULL;
    long mcblen;
    PyObject *retval;
    PyObject *empty_tuple;

    // parse arguments... 
    if (!PyArg_ParseTuple(args, "sls#l", &file_name, &sz, &mcb, &mcblen, &out )){
        PyErr_SetString( PyExc_ValueError, 
	  "requires 6 arguments: filename (/dev/sd?), length, mcb, out-boolean" );
        return(NULL);
    }

    /* N.B. An access mode of O_RDWR is required for some SCSI commands */
    if ((sg_fd = open(file_name, O_RDONLY)) < 0) {
        PyErr_SetFromErrnoWithFilename( PyExc_OSError, file_name );
        return(NULL);

    }

    empty_tuple=PyTuple_New(0);

    /* Just to be safe, check we have a new sg device by trying an ioctl */
    if ((ioctl(sg_fd, SG_GET_VERSION_NUM, &k) < 0) || (k < 30000)) {
        PyErr_SetFromErrnoWithFilename( PyExc_OSError, file_name );
        close(sg_fd);
        return(NULL);
    }

    buffer = PyMem_Malloc(sz);
    if (buffer == NULL) {
        PyErr_SetString( PyExc_RuntimeError, "failed to allocate read buffer");
    }
    //buffer=calloc(sz,1);
    bzero(buffer,sz);
 
    szwritten = get_mode_page(sg_fd, buffer, sz, mcb, mcblen, out);
    if (szwritten > 0)  {
         retval = PyString_FromStringAndSize(buffer, szwritten );
    } else {
         PyErr_SetFromErrnoWithFilename( PyExc_OSError, file_name );
         return(NULL);
    }
    close(sg_fd);
    PyMem_Free(buffer);
    return(retval);
};

static PyMethodDef DroboDMPMethods[] = {
    { "get_sub_page", drobodmp_get_sub_page, METH_VARARGS|METH_KEYWORDS, 
                  "retrieve a Drobo Management Protocol formatted scsi control block" },
    { NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC initDroboDMP(void) {

  (void) Py_InitModule("DroboDMP", DroboDMPMethods );
}

