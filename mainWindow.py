# ----------- testes criando janelas para o programa... create the root window
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.messagebox import showinfo

class mainWindow:
    # root=None
    # tBox=None
    # bAbrir=None
    # bFechar=None
    
    # definições e propriedades
    def __init__(self) -> None:
        self.root =  tk.Tk()
        self.root.title('Testes...')
        self.root.resizable(True, True)
        self.root.geometry('600x600')
    #     pass
    
    ## métodos
    def select_file(self) -> [bool, str]:
        filetypes = (
            ('text files', '*.txt'),
            ('Arquivos Wave', '*.wav'),
            ('All files', '*.*')
        )

        filename = filedialog.askopenfilename(
            title='Open a file',
            initialdir='/',
            filetypes=filetypes)

        if len(filename) > 0:
            showinfo(
            title='Selected File',
            message=filename
            )
        return len(filename)>0,filename
    
    def donothing(self):
        filewin = tk.Toplevel(self.root) # cria uma nova janela sobre a principal (util para dialogs)
        filewin.geometry('400x200')
        button = tk.Button(filewin, text="Do nothing button")
        button.pack()
                
    def read_wav(self, data):
        ret,filename=self.select_file()
        if ret:
            import wave, io
            with wave.open(io.BytesIO(data)) as wave_file:
                wave_data = wave_file.readframes(wave_file.getnframes())
                num_samples = wave_file.getnframes() * wave_file.getnchannels()
                return io.struct.unpack('<%sh' % num_samples, wave_data)
    
    def openWavAudio(self):
        ret,filename=self.select_file() 
        if ret:
            import wave
            wav_obj = wave.open(filename, 'rb')
            n_samples = wav_obj.getnframes()
            n_channels = wav_obj.getnchannels()
            sample_freq = wav_obj.getframerate()
            sw = wav_obj.getsampwidth()
            t_audio = n_samples/sample_freq
            signal_wave = wav_obj.readframes(n_samples)
            import numpy as np
            signal_array = np.frombuffer(signal_wave, dtype=np.int16)
            l_channel = signal_array[0::2]
            r_channel = signal_array[1::2]
            times = np.linspace(0, n_samples/sample_freq, num=n_samples)
            import scipy as sp
            import matplotlib.pyplot as plt

            
            plt.figure(figsize=(15, 5))
            plt.plot(l_channel)
            plt.title('Left Channel')
            plt.ylabel('Signal Value')
            plt.xlabel('Time (s)')
            plt.xlim(0, t_audio)
            plt.show()
            return (n_samples, n_channels, sample_freq, sw)
    	
    def changeFont(self):
        Font_tuple = ("Comic Sans MS", 20, "bold")
        self.tBox.configure(font=Font_tuple)
        
    def cleargarbage(self):
        pass
    
    def addMenu(self):
        ## menu principal da janela
        menubar = tk.Menu(self.root)
        
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=self.donothing)
        filemenu.add_command(label="Open", command=self.openWavAudio)
        filemenu.add_command(label="Save", command=self.donothing)
        filemenu.add_command(label="Save as...", command=self.donothing)
        filemenu.add_command(label="Close", command=self.donothing)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        
        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="Undo", command=self.changeFont)
        editmenu.add_separator()
        editmenu.add_command(label="Cut", command=self.donothing)
        editmenu.add_command(label="Copy", command=self.donothing)
        editmenu.add_command(label="Paste", command=self.donothing)
        editmenu.add_command(label="Delete", command=self.donothing)
        editmenu.add_command(label="Select All", command=self.donothing)
        menubar.add_cascade(label="Edit", menu=editmenu)
        
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Help Index", command=self.donothing)
        helpmenu.add_command(label="About...", command=self.donothing)
        menubar.add_cascade(label="Help", menu=helpmenu)

        return self.root.config(menu=menubar)
    
    def addButton(self, _command=None, _title='button', _x=0, _y=0) -> tk.Button:
        return tk.Button(
                        self.root,
                        text=_title,    
                        command=_command,
                        padx=10, #largura do botão
                        pady=10  #altura do botão                      
                    ).place(x = _x , y = _y)
        
    def addTextBox(self) -> tk.Text:
        return tk.Text(   # Create text widget and specify size.
                    self.root, 
                    height = 5, 
                    width = 52,
                    wrap='word'
                    ).pack(expand=True, side='bottom')     
    
        
    def createmainWindow(self):
        self.addMenu()
        self.bAbrir = self.addButton(_command = self.select_file, _title='Abrir um arquivo', _x=10, _y=10)
        self.bFechar = self.addButton(_command = self.root.destroy, _title='Fechar janela',   _x=10, _y=60)
        self.tBox = self.addTextBox()
'''        
# parallel CPU - testes
# https://saturncloud.io/blog/python-parallelizing-gpu-and-cpu-work/#:~:text=Parallelizing%20GPU%20work%20involves%20using,pycuda%20%2C%20numba%20%2C%20and%20tensorflow%20.
# Joblib
import joblib
def square(x):
    return x**2
    
if __name__ == '__main__':
    results = joblib.Parallel(n_jobs=-1)(joblib.delayed(square)(i) for i in range(100))
    print(results)


#Parallel GPU - testes    
# Tensorflow
import tensorflow as tf
import numpy as np
from timeit import default_timer as timer

def psquare(x):
    return tf.square(x)
    
def square(x):
	return x*x

if __name__ == '__main__':
    m=range(1000)
    result=np.array(m)
    print(result)
    
    t0=timer()    
    for i in m:
    	result[i]=square(i)
    
    print(f'Sem paralelismo: {timer() - t0} segundos')
    print(result)
    
    t0=timer()
    with tf.device('/device:GPU:0'):        
        a=tf.constant(np.array(m).astype(np.float32))
        #a = tf.constant(np.array([1, 2, 3, 4, 5]).astype(np.float32))
        result = psquare(a)
        
    print(f'Com paralelismo: {timer() - t0} segundos') 
    print(result)

# Numba
import numba
import numpy as np

@numba.jit(nopython=True, parallel=True)
def square(array):
    for i in numba.prange(len(array)):
        array[i] = array[i] * array[i]
    return array

if __name__ == '__main__':
    a = np.array([1, 2, 3, 4, 5]).astype(np.float32)
    result = square(a)
    print(result)

# Tensorflow
import tensorflow as tf
import numpy as np

def square(x):
    return tf.square(x)

if __name__ == '__main__':
    with tf.device('/device:GPU:0'):
        m=range(100)
        print(m)
        a=m
        #a = tf.constant(np.array([1, 2, 3, 4, 5]).astype(np.float32))
        result = square(a)
        print(result.numpy())
'''
   
if __name__ == '__main__':
    p = mainWindow()
    p.createmainWindow()
    p.root.mainloop()
# -------------------------------------------------------------------
