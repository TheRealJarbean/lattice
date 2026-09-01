import cv2

def main():
    index = 0
    arr = []
    print("Made it to loop!")
    while index <= 10:
        print(f"Check camera at index {index}")
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
        print(cap.getBackendName())
        if not cap.read()[0]:
            print("No camera found at index")
            break
        else:
            print("Adding to index!")
            arr.append(index)
        cap.release()
        index += 1
    print(arr)

if __name__ == "__main__":
    main()