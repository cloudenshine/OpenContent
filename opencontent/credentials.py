"""Windows user-bound DPAPI; other platforms use an explicit environment variable."""
import ctypes
import os
import re
from .vault import Problem, atomic


def crypt(raw, decrypt=False):
    if os.name!='nt':raise Problem('Use a password environment variable on this platform')
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    buffer=ctypes.create_string_buffer(raw)
    source=Blob(len(raw),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)));target=Blob()
    lib=ctypes.WinDLL('crypt32',use_last_error=True)
    fn=lib.CryptUnprotectData if decrypt else lib.CryptProtectData
    fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    fn.restype=wintypes.BOOL
    if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(target)):
        raise Problem('Windows credential protection failed; configure credentials for the current Windows user',503)
    free=ctypes.WinDLL('kernel32').LocalFree;free.argtypes=[ctypes.c_void_p];free.restype=ctypes.c_void_p
    try:return ctypes.string_at(target.data,target.size)
    finally:free(target.data)


def save(vault, key, password):
    if not isinstance(key,str) or not re.fullmatch(r'[0-9a-f]{32}',key):raise Problem('Invalid credential key')
    if not isinstance(password,str) or not 1<=len(password)<=4096:raise Problem('Invalid application password')
    atomic(vault.safe('.opencontent/credentials/'+key+'.bin'),crypt(password.encode()))


def load(vault, config):
    if config.get('password_env'):
        result=os.environ.get(config['password_env'],'')
        if not result:raise Problem('The configured application password environment variable is unavailable',503)
        return result
    key=config['credential_id']
    if not isinstance(key,str) or not re.fullmatch(r'[0-9a-f]{32}',key):raise Problem('Invalid credential key')
    path=vault.safe('.opencontent/credentials/'+key+'.bin')
    if not path.exists():raise Problem('Configure an application password for this channel',503)
    return crypt(path.read_bytes(),True).decode()
