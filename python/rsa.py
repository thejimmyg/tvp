# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

'''
openssl genpkey -algorithm RSA -out private_key.pem -pkeyopt rsa_keygen_bits:2048
openssl rsa -pubout -in private_key.pem -out public_key.pem
python3 test.py
'''

import os
import ctypes
import base64
import hashlib
from ctypes import POINTER, c_int, c_void_p, c_char_p, c_size_t

# Load OpenSSL shared library
libcrypto = ctypes.cdll.LoadLibrary(os.environ['LIBCRYPTO'])


# Define argument and return types for the OpenSSL functions we'll use
libcrypto.RSA_sign.argtypes = [c_int, ctypes.c_char_p, c_size_t, ctypes.c_char_p, POINTER(c_int), c_void_p]
libcrypto.RSA_sign.restype = c_int

libcrypto.RSA_verify.argtypes = [c_int, ctypes.c_char_p, c_size_t, ctypes.c_char_p, c_size_t, c_void_p]
libcrypto.RSA_verify.restype = c_int

libcrypto.BIO_new_mem_buf.argtypes = [c_void_p, c_int]
libcrypto.BIO_new_mem_buf.restype = c_void_p

libcrypto.PEM_read_bio_RSAPrivateKey.argtypes = [c_void_p, POINTER(c_void_p), c_void_p, c_void_p]
libcrypto.PEM_read_bio_RSAPrivateKey.restype = c_void_p

libcrypto.PEM_read_bio_RSA_PUBKEY.argtypes = [c_void_p, POINTER(c_void_p), c_void_p, c_void_p]
libcrypto.PEM_read_bio_RSA_PUBKEY.restype = c_void_p

libcrypto.BIO_free.argtypes = [c_void_p]
libcrypto.BIO_free.restype = c_int

NID_sha256 = 672  # This is the identifier for SHA-256


def rsa_sign(private_key, message):
    digest = hashlib.sha256(message).digest()
    siglen = c_int()
    signature = ctypes.create_string_buffer(256)  # Adjust size for key length
    result = libcrypto.RSA_sign(NID_sha256, digest, len(digest), signature, ctypes.byref(siglen), private_key)
    if result != 1:
        raise Exception("RSA_sign failed")
    return signature.raw[:siglen.value]


def rsa_verify(public_key, message, signature):
    digest = hashlib.sha256(message).digest()
    result = libcrypto.RSA_verify(NID_sha256, digest, len(digest), signature, len(signature), public_key)
    return result == 1


def load_private_key(filepath):
    with open(filepath, 'rb') as f:
        private_key_pem = f.read()
    
    bio = libcrypto.BIO_new_mem_buf(private_key_pem, len(private_key_pem))
    if not bio:
        raise Exception("Failed to create BIO for private key")
    
    private_key = libcrypto.PEM_read_bio_RSAPrivateKey(bio, None, None, None)
    libcrypto.BIO_free(bio)
    
    if not private_key:
        raise Exception("Failed to load private key")
    
    return private_key


def load_public_key(filepath):
    with open(filepath, 'rb') as f:
        public_key_pem = f.read()
    
    bio = libcrypto.BIO_new_mem_buf(public_key_pem, len(public_key_pem))
    if not bio:
        raise Exception("Failed to create BIO for public key")
    
    public_key = libcrypto.PEM_read_bio_RSA_PUBKEY(bio, None, None, None)
    libcrypto.BIO_free(bio)
    
    if not public_key:
        raise Exception("Failed to load public key")
    
    return public_key


def base64_url_encode(data):
    """Base64 URL encode the data."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')


# Load keys
private_key = load_private_key('private_key.pem')
public_key = load_public_key('public_key.pem')

# Example message to sign
message = b'Hello, this is a test message.'

# Sign the message
signature = rsa_sign(private_key, message)

# Base64 URL encode the signature
encoded_signature = base64_url_encode(signature)
print(f"Base64 URL Encoded Signature: {encoded_signature}")

# Verify the signature
is_valid = rsa_verify(public_key, message, signature)
print(f"Is the signature valid? {is_valid}")
