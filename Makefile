DESTDIR=
PREFIX=/usr
NAME=ec2utilsbase
dirs = lib
files = Makefile README.md LICENSE setup.py

nv = $(shell rpm -q --specfile --qf '%{NAME}-%{VERSION}\n' *.spec)
verSpec = $(shell rpm -q --specfile --qf '%{VERSION}' *.spec)
verSrc = $(shell cat lib/ec2utils/base_VERSION)
ifneq "$(verSpec)" "$(verSrc)"
$(error "Version mismatch, will not take any action")
endif

clean:
	@find . -name "*.pyc" | xargs rm -f 
	@find . -name "__pycache__" | xargs rm -rf
	@find . -name "*.cache" | xargs rm -rf
	@find . -name "*.egg-info" | xargs rm -rf

pep8: clean
	@pep8 -v --statistics lib/ec2utils/*
	@pep8 -v --statistics --ignore=E402 tests/*.py

tar: clean
	rm -rf $(NAME)-$(verSrc)
	mkdir $(NAME)-$(verSrc)
	cp -r $(dirs) $(files) "$(NAME)-$(verSrc)"
	tar -cjf "$(NAME)-$(verSrc).tar.bz2" "$(NAME)-$(verSrc)"
	rm -rf "$(NAME)-$(verSrc)"

test:
	py.test tests/ec2utilsutilstest.py

pypi:
	mkdir -p "$(NAME)-$(verSrc)"/man/man1
	cp -r $(dirs) $(files) "$(NAME)-$(verSrc)"
	tar -czf "$(NAME)-$(verSrc).tar.gz" "$(NAME)-$(verSrc)"
	rm -rf "$(NAME)-$(verSrc)"
	mkdir dist
	mv "$(NAME)-$(verSrc).tar.gz" dist

install:
	python setup.py install --prefix="$(PREFIX)" --root="$(DESTDIR)"
