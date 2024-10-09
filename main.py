import argparse, collections, difflib, enum, hashlib, operator, os, stat
import struct, sys, time, urllib.request, zlib

class Repository:
    def __init__(self, repo):
        try:
        #Create a dict for repo and initialize .git directory
            os.mkdir(repo)
            os.mkdir(os.path.join(repo, '.git'))
            for name in ['objects', 'refs', 'refs/heads']:
                os.mkdir(os.path.join(repo, '.git', name))

        #write to the head file
            with open(os.path.join(repo, '.git', 'HEAD'),'wb') as head_file:
                head_file.write(b'ref: refs/heads/main\n')
            print('initialized empty repository: {}'.format(repo))
    
        except FileExistsError:
            print(f"Error: The directory '{repo}' already exists.")
        
        except Exception as e:
            print(f"An error occured: {e}")
            
    def hash_objects(self, data, obj_type, write=True):
        """Compute hash of object data of given type and write to object store
        if 'write' is True. Return SHA-1 object has as hex string."""
        header = '{} {}'.format(obj_type, len(data)).encode()
        full_data = header + b'\x00' + data
        sha1 = hashlib.sha1(full_data).hexdigest()
        print('Computed SHA-1 hash:', sha1)
        if write:
            path = os.path.join('.git', 'objects', sha1[:2], sha1[2:])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as file_write:
                file_write.write(zlib.compress(full_data))
        return sha1
    
    IndexEntry = collections.namedtuple('IndexEntry', [
        'ctime_s', 'ctime_n', 'mtime_s', 'mtime_n', 'dev', 'ino', 'mode',
        'uid', 'gid', 'size', 'sha1', 'flags', 'path',
    ])
    
    def read_index():
        #Read git index file and return list of Index Entry objects
        data_path = os.path.join('.git', 'index')
        try:
            with open(data_path, "r") as data:
                content = data.read()
        except FileNotFoundError:
            return []
        print(content)
        
            
            
        



if __name__ == "__main__":
    repo_name = "my_repo"
    repo = Repository(repo_name)

    data = b"This works"
    obj_type = "blob"
    
    sha1_hash = repo.hash_objects(data, obj_type)
    print('SHA-1 hash:', sha1_hash)