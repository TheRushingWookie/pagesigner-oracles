#get hashes of old version's oracle snapshots
#First hash file/directory/symlink paths, ownership, permissions, and symlink targets.
#Then hash the contents of all regular files.

#for sort
export LC_ALL=C 
> /tmp/1
cd /mnt/notary_oracle
find . -printf '%h %f %U %G %m %l\n' | sort -t \n > /tmp/fs
hash1=$(find . -printf '%h %f %U %G %m %l\n' | sort -t \n | sha256sum | cut -d ' ' -f 1)
hash2=$(find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d ' ' -f 1)

cd /mnt/signing_oracle
hash3=$(find . -printf '%h %f %U %G %m %l\n' | sort -t \n | sha256sum | cut -d ' ' -f 1)
hash4=$(find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d ' ' -f 1)

> /tmp/2
sudo -u ubuntu python3 /dev/shm/notary/migrate/check_hashes.py $hash1 $hash2 $hash3 $hash4
echo $? > /tmp/3
#the exit code should be 123 - only then we proceed to start the notary server
if [ $? -eq 123 ]; then sudo -u ubuntu python3 /dev/shm/notary/notaryserver.py; fi