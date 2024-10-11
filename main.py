import argparse, collections, difflib, enum, hashlib, operator, os, stat
import struct, sys, time, urllib.request, zlib

#Data for one entry in the git index(.git/index)
IndexEntry = collections.namedtuple('IndexEntry', [
        'ctime_s', 'ctime_n', 'mtime_s', 'mtime_n', 'dev', 'ino', 'mode',
        'uid', 'gid', 'size', 'sha1', 'flags', 'path',
    ])
    


class ObjectType(enum.Enum):
    
    commit = 1
    tree = 2
    blob = 3
    
def read_file(path):
    with open(path, 'rb') as f:
        return f.read()

def write_file(path, data):
    with open(path, 'wb') as f:
        f.write(data)

def init(repo):
    #Create a dict for repo and initialize .git directory
    os.mkdir(repo)
    os.mkdir(os.path.join(repo, '.git'))
    for name in ['objects', 'refs', 'refs/heads']:
        os.mkdir(os.path.join(repo, '.git', name))
    #write to the head file
    write_file(os.path.join(repo, '.git', "HEAD"),
               b'ref: refs/heads/main')
    print('initialized empty repository: {}'.format(repo))
    
def hash_objects(data, obj_type, write=True):
    """Compute hash of object data of given type and write to object store
    if 'write' is True. Return SHA-1 object has as hex string."""
    header = '{} {}'.format(obj_type, len(data)).encode()
    full_data = header + b'\x00' + data
    sha1 = hashlib.sha1(full_data).hexdigest()
    print('Computed SHA-1 hash:', sha1)
    if write:
        path = os.path.join('.git', 'objects', sha1[:2], sha1[2:])
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            write_file(path, zlib.compress(full_data))
    return sha1

def find_object(sha1_prefix):
    """Find object with given sha-1 prefix and return path to object in object
    store, or raise ValueError if there are no objects or multiple with this prefix."""
    if len(sha1_prefix) < 2:
        raise ValueError('hash prefix must be 2 ore more characters')
    obj_dir = os.path.join('.git', 'objects', sha1_prefix[:2])
    rest = sha1_prefix[2:]
    objects = [name for name in os.listdir(obj_dir) if name.startswith(rest)]
    if not objects:
        raise ValueError('object {!r} not found'.format(sha1_prefix))
    if len(objects) >= 2:
        raise ValueError('multiple objects ({}) with prefix {!r}'.format(
            len(objects), sha1_prefix))
    return os.path.join(obj_dir, objects[0])

def read_object(sha1_prefix):
    """Read object with given sha-1 prefix and return tuple of
    (object_type, data_bytes) or raise ValueError if not found"""
    path = find_object(sha1_prefix)
    full_data = zlib.decompress(read_file(path))
    nul_index = full_data.index(b'\x00')
    header = full_data[:nul_index]
    obj_type, size_str = header.decode().split()
    size = int(size_str)
    data = full_data[nul_index + 1:]
    assert size == len(data), 'expected size {}, got {} bytes'.format(
        size, len(data))
    return (obj_type, data)

def cat_file(mode, sha1_prefix):
    """Write the contents of (or info about) object with given sha-1 prefix
    to stdout. If mode is 'commit', 'tree', or 'blob', print raw data bytes
    of object. If mode is 'size', print the size of the object. If mode is 
    'type', print the type of the object. If mode is 'pretty', print a 
    prettified version of the object."""
    
    obj_type, data = read_object(sha1_prefix)
    if mode in ['commit', 'tree', 'blob']:
        if obj_type != mode:
            raise ValueError('expected object type {}, got {}'.format(
                mode, obj_type))
        sys.stdout.buffer.write(data)
    elif mode == 'size':
        print(len(data))
    elif mode == 'type':
        print(obj_type)
    #elif mode == 'pretty':
    #    if obj_type in ['commit', 'blob']:
    #        sys.stdout.buffer.write(data)
    #    elif obj_type == 'tree':
    #        for mode, path, sha1 in read_tree(data=data):
    #            type_str = 'tree' if stat.S_ISDIR(mode) else 'blob'
    #            print('{:06o} {} {}\t{}'.format(mode, type_str, sha1, path))
        #else:
        #    assert False, 'unhandled object type {!r}'.format(obj_type)
    else:
        raise ValueError('unexpected mode {!r}'.format(mode))
   
     
def read_index():
    #Read git index file and return list of IndexEntry objects
    data_path = os.path.join('.git', 'index')
    try:
        with open(data_path, "r") as data:
            content = data.read()
    except FileNotFoundError:
        return []
    digest = hashlib.sha1(data[:-20]).digest()
    assert digest == data[-20:], 'invalid index checksum'
    signature, version, num_entries = struct.unpack('!4sLL', data[:12])
    assert signature == b'DIRC', \
        'invalid index signature {}'.format(signature)
    assert version == 2, 'unknown index version {}'.format(version)
    entry_data = data[12:-20]
    entries = []
    i = 0
    while i + 62 < len(entry_data):
        fields_end = i + 62
        fields = struct.unpack('!LLLLLLLLLL20sH',
                               entry_data[i:fields_end])
        path_end  = entry_data.index(b'\x00', fields_end)
        path = entry_data[fields_end:path_end]
        entry = IndexEntry(*(fields + (path.decode(), )))
        entries.append(entry)
        entry_len = ((62 + len(path) + 8) // 8) * 8
        i += entry_len
        
    assert len(entries) == num_entries
    return entries


        
        
            
        



if __name__ == "__main__":
    repo_name = "my_repo"
    if not os.path.exists(repo_name):
        init(repo_name)
    data = b"This works"
    obj_type = "blob"
    
    sha1_hash = hash_objects(data, obj_type)
    print('SHA-1 hash:', sha1_hash)