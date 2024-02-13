import pickle, os, bz2, shutil

def create_folder(FolderPath):
    try:
        os.mkdir(FolderPath)
    except FileExistsError:
        shutil.rmtree(FolderPath)
        os.mkdir(FolderPath)

def load_data(Path, FileName, compress=True):
    data_path = os.path.join(Path, FileName)
    if compress:
        ifile = bz2.BZ2File(data_path, 'rb')
        data = pickle.load(ifile)
        ifile.close()
    else:
        with open(data_path, 'rb') as file:
            data = pickle.load(file)

    return data

def store_data(Path, FileName, data, SubFolder=False, FolderName=None, compress=True):
    if SubFolder:
        folder_path = os.path.join(Path, FolderName)
        try:
            os.mkdir(folder_path)
        except FileExistsError:
            pass

        data_path = os.path.join(folder_path, FileName)
    else:
        data_path = os.path.join(Path, FileName)

    if compress:
        ofile = bz2.BZ2File(data_path, 'wb')
        pickle.dump(data, ofile)
        ofile.close()
    else:
        with open(data_path, 'wb') as file:
            pickle.dump(data, file)
