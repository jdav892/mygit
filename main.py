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
            
if __name__ == "__main__":
    repo_name = "my_repo"
    repo = Repository(repo_name)
    