double bestBid() const { return bids_.empty() ? 0.0 : bids_.rbegin()->first; }
double bestAsk() const { return asks_.empty() ? 0.0 : asks_.begin()->first; }
// Why both of them are O(1)?
// As we have pointer pointing to the smallest and highest value
// default are in accesding orders
// However, for bids we are looking for the largest bid
// ask we are looking for the smallest ask.
// Therefore, we are returning two points 1 for largest and 1 for smallest.
