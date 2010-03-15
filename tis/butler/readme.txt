Tis project was developed as a prototype malware traffic analyser. It's quite scripty, so use at your own peril.

	Files:			Description:
	butler.py		Scripter, setting up and controlling the virtual machines, and logging.
	AttachFile.py		required scripts, that are imported by butler.py
	live_md5archive.txt	md5 hashes, used for checking, if analysis is required on this sample.




file structure:
	server:
		FILENAME		FOLDER					RIGHTS?			
		butler.py		foo/					rx
		AttachFile.py		foo/					rx
		editing.py		foo/					rx
		
		live_md5archive.txt	foo/md5archive/live_md5archive.txt	rw

		./mwfolder		foo/mwfolder/				rw	Where malware is read from (to be analyzed)
		./mw_cemetary		foo/mw_cemetary/			w	After the malware is analyzed, it's put here

		x.iso			??					rw	Malware is made to .iso file for insertation into the analysis system
		
		./toolz/		foo/toolz/				rx	Folder for 3rd party yools

	tis (total internet simulator) image:
		malwarezor/		/var/www/malwarezor/			rwx	Apache folder used to share the malware sample to the victim (online)
		prosessed/		/Malpractice/prosessed/			rw	Where the prosessed malware sample is moved to
		cdrom1			/media/cdrom1				r	the malware .iso file, defined to be the cdrom in the virtual image

3rd party Dependensies:
- server
	graphing wiki	A wiki, with graphing functions. butler.py
	strings		Finds strings that are in the malware file (butler.py)
	tcpdump		requires su rights (butler.py)

-vic image	
	unzip


Deploying:
	Server machine:
		butler.py

	The Internet Simulator - virtual image:
		tis_script.py

	The victim image:
		vic_uploader.py