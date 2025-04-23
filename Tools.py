from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QImage


def receive_big_data(socket):
    data_size = int(socket.recv(1024).decode())
    socket.send(b"SIZE_RECEIVED")
    # data_name = data["data_name"]
    data = b''
    while data_size > 0:
        data += socket.recv(1024)
        data_size -= 1024
    return data


def send_big_data(socket, data):
    data_size = len(data)  # Use len() for accurate size calculation, not sys.getsizeof
    print(f"sending big data to server file size: {data_size} data: {data}")

    # First send the size as a fixed-size 4-byte integer (standard method for sending data size)
    socket.sendall(data_size.to_bytes(4, byteorder='big'))

    # Then send the actual data
    socket.sendall(data)


def pixmap_to_byte_array(pixmap):
    # Convert QPixmap to QByteArray
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, 'PNG')  # Save the pixmap as PNG format in the byte array
    return byte_array


def image_to_byte_array(image: QImage):
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, 'PNG')  # Save the pixmap as PNG format in the byte array
    return byte_array


def byte_array_to_image(byte_array):
    # Convert byte array to QByteArray (if needed)
    image = QImage()
    image.loadFromData(byte_array)
    return image
