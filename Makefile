
NAME = taskmaster

all: $(NAME)

$(NAME): 
	@ make -C ./42sh
	export PATH=$(PATH):./42sh

clean: 
	@ make clean -C ./42sh

fclean: clean
	@ make fclean -C ./42sh

re: fclean all
