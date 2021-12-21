#include<iostream>

auto A=[](int x){
	std::cout<<x<<'\n';
	return x+1;
};

// recursive lambda (global)
auto B=[](auto B, int x)->int{
	if(x>=0) return B(B, x-1)+1;
	return 1;
};

auto C=[]{
	B(B, 5);
};

int main(){
	int y=1;

	auto a=[&](int x){
		y+=1;
		return x+1;
	};

	auto a2=[&](int x){
		return x+1;
	};

	auto const& a3=[&](int x){
		return x+1;
	};

	// recursive lambda
	auto b=[&](auto b, int x)->int{
		if(x>=0) return b(b, x-1)+1;
		return 1;
	};

	// need to call for compiler to instantiate the template
	b(b, 5);
	B(B, 5);

	__builtin_trap();
}
