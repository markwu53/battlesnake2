import math
#n*n -7x=2

for n in range(1, 100):
    if (n**2-2) % 7 == 0:
        x = (n**2 - 2) // 7
        y = math.isqrt(x)
        if y * y == x:
            print(f"n: {n}, x: {x}")


