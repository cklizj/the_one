auto a{1};
auto b{1,2,3};

// What are the type for the a ? that will be a int
// how about b? do u think that will be a vector?
// expensive.
// This is a std::initializer_list<int>
// This is a auto detection with using auto
// However, for this type of thing, there is one more thing about it --> template

template<T>
auto to_do_something(T){

}

// However why this is wrong with initializer?
// It will be over-generalized.
