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

def ls_files(details=False):
    """Print lists of files in index (including mode, sha-1 and stage number
    if details is true.)"""
    for entry in read_index():
        if details:
            stage = (entry.flags >> 12) & 3
            print('{:6o} {} {:}\t{}'.format(
                    entry.mode, entry.sha1.hex(), stage, entry.path))
        else:
            print(entry.path)
            
def get_status():
    """Gets status of working copy, return tuple of(changed_paths, new_paths,
    deleted_paths)."""
    
    paths = set()
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d != '.git']
        for file in files:
            path = os.path.join(root, file)
            path = path.replace('\\', '/')
            if path.startswith('./'):
                path = path[2:]
            paths.add(path)
        entries_by_path = {e.path: e for e in read_index()}
        entry_paths = set(entries_by_path)
        changed = {p for p in (paths & entry_paths) 
                   if hash_objects(read_file(p), 'blob', write=False) != 
                   entries_by_path[p].sha1.hex()}
        new = paths - entry_paths
        deleted = entry_paths - paths
        return (sorted(changed), sorted(new), sorted(deleted))
    
def status():
    #Show status of working copy
    changed, new, deleted = get_status()
    if changed:
        print('changed files:')
        for path in changed:
            print('   ', path)
    
    if new:
        print('new files:')
        for path in new:
            print('   ', path)
    
    if deleted:
        print('deleted files:')
        for path in deleted:
            print('   ', path)
            
def diff():
    #Show diff of files changed(between index and working copy.)
    changed, _, _ = get_status()
    entries_by_path = {e.path: e for e in read_index()}
    for i, path in enumerate(changed):
        sha1 = entries_by_path[path].sha1.hex()
        obj_type, data = read_object(sha1)
        assert obj_type == 'blob'
        index_lines = data.decode().splitlines()
        working_lines = read_file(path).decode().splitlines()
        diff_lines = difflib.unified_diff(
            index_lines, working_lines,
            '{} (index)'.format(path),
            '{} (working copy)'.format(path),
            lineterm='')
        for line in diff_lines:
            print(line)
        if i < len(changed) - 1:
            print('-' * 70)
           
def write_index(entries):
    #Write a list of IndexEntry objects to git index
    packed_entries = []
    for entry in entries:
        entry_head = struct.pack('!LLLLLLLLLL20sH',
                entry.ctime_s, entry.ctime_n, entry.mtime_s, entry.mtime_n,
                entry.dev, entry.ino, entry.mode, entry.uid, entry.gid,
                entry.size, entry.sha1, entry.flags)
        path = entry.path.encode()
        length = ((62 + len(path) + 8) // 8) * 8
        packed_entry = entry_head + path + b'\x00' * (length - 62 - len(path))
        packed_entries.append(packed_entry)
    header = struct.pack('4sLL', b'DIRC', 2, len(entries))
    all_data = header + b''.join(packed_entries)
    digest = hashlib.sha1(all_data).digest()
    write_file(os.path.join('.git', 'index'), all_data + digest)
    

def add(paths):
    #Add all file paths to git index
    paths = [p.replace('\\', '/') for p in paths]
    all_entries = read_index()
    entries = [e for e in all_entries if e.path not in paths]
    for path in paths:
        sha1 = hash_objects(read_file(path), 'blob')
        st = os.stat(path)
        flags = len(path.encode())
        assert flags < (1 << 12)
        entry = IndexEntry(
            int(st.st_birthtime), 0, int(st.st_mtime), 0, st.st_dev,
            st.st_ino, st.st_mode, st.st_uid. st.st_gid, st.st_size,
            bytes.fromhex(sha1), flags, path)
        entries.append(entry)
    entries.sort(key=operator.attrgetter('path'))
    write_index(entries)
          
def write_tree():
    #Write a tree object from the current index entries
    tree_entries = []
    for entry in read_index():
        assert '/' not in entry.path, \
            'current only supports a single top level dir'
        mode_path = '{:o} {}'.format(entry.mode, entry.path).encode()
        tree_entry = mode_path + b'\x00' + entry.sha1
        tree_entries.append(tree_entry)
    return hash_objects(b''.join(tree_entries), 'tree')

def get_local_main_hash():
    #Get current commit hash (sha1 string) of local main branch
    main_path = os.path.join('.git', 'refs', 'heads', 'main')
    try:
        return read_file(main_path).decode().strip()
    except FileNotFoundError:
        return None
    
def commit(message, author):
    """Commit the current state of the index to master with given
    message. Return hash of commit object."""
    tree = write_tree()
    parent = get_local_main_hash()
    if author is None:
        author = '{} <{}>'.format(
            os.environ['GIT_AUTHOR_NAME'], os.environ['GIT_AUTHOR_EMAIL'])
    timestamp = int(time.mktime(time.localtime()))
    utc_offset = -time.timezone
    author_time = '{} {} {:02}{:02}'.format(
        timestamp,
        '+' if utc_offset > 0 else '-',
        abs(utc_offset) // 3600,
        (abs(utc_offset) // 60) % 60)
    lines = ['tree' + tree]
    if parent:
        lines.append('parent' + parent)
    lines.append('author {} {}'.format(author, author_time))
    lines.append('committer {} {}'.format(author, author_time))
    lines.append('')
    lines.append(message)
    lines.append('')
    data = '\n'.join('lines').encode()
    sha1 = hash_objects(data, 'commit')
    main_path = os.path.join('.git', 'refs', 'heads', 'main')
    write_file(main_path, (sha1 + '\n').encode())
    print('committed to main: {:7}'.format(sha1))
    return sha1 
        
            
        



if __name__ == "__main__":
    repo_name = "my_repo"
    if not os.path.exists(repo_name):
        init(repo_name)
    data = b"This works"
    obj_type = "blob"
    
    sha1_hash = hash_objects(data, obj_type)
    print('SHA-1 hash:', sha1_hash, repo_name)