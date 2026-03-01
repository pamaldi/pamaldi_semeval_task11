% Facts for the premises
cloud(whitestorm).
sheep(lamb1).

% Facts for the common attribute (white)
white(whitestorm).
white(lamb1).

% Validity check: All sheep are clouds → For all sheep, they must also be clouds
valid_syllogism :- \+ (sheep(X), \+ cloud(X)).