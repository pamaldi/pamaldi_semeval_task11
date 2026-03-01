% Facts: some books are not digital files (witness)
book(b1).
\+ digital_file(b1).

% All books are items with pages
item_with_pages(X) :- book(X).

% Validity check: Some items with pages are digital files
valid_syllogism :- item_with_pages(X), digital_file(X).