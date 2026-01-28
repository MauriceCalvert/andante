from builder.config_loader import load_genre
from planner.treatment_generator import generate_for_genre

g = load_genre("invention")
print("Invention treatments:", g.treatments)
print("Generated sequence:", generate_for_genre(g, 8))

g2 = load_genre("minuet")
print("\nMinuet treatments:", g2.treatments)
print("Generated sequence:", generate_for_genre(g2, 4))
