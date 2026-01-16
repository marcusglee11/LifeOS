import utils

def main():
    print("Running math operations...")
    print(f"2 + 3 = {utils.add(2, 3)}")
    print(f"5 * 4 = {utils.multiply(5, 4)}")
    
    print("\nRunning string operations...")
    text = "Hello World"
    print(f"'{text}' reversed: {utils.reverse_string(text)}")
    print(f"'{text}' uppercase: {utils.to_uppercase(text)}")

if __name__ == "__main__":
    main()
