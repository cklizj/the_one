int main{

    struct Loc{
	bool isBuy;
	double price;
	std::list<Order>::iterator it;
        }
    //
    std::unordermap<uint64_t, Loc> for_cancel;
    auto default_loc = for_cancel[id] // what if we have a unknown id?
    // what are the default behavior?
    // It is going to create for bool = False, price = 0.0, and iterator are going to returen a dangling pointer.
    // very dangerous.
}
