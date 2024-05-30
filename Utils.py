# utilitários
import ctypes  # An included library with Python install.

class Utils:


# Print iterations progress
    def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            length      - Optional  : character length of bar (Int)
            fill        - Optional  : bar fill character (Str)
            printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
        """
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
        # Print New Line on Complete
        if iteration == total: 
            print()

    
    def Mbox(title, text, style=0):  
        '''
        ##  Styles:
        ##  0 : OK
        ##  1 : OK | Cancel
        ##  2 : Abort | Retry | Ignore
        ##  3 : Yes | No | Cancel
        ##  4 : Yes | No
        ##  5 : Retry | Cancel 
        ##  6 : Cancel | Try Again | Continue
        # uso:
        ##  Mbox('Your title', 'Your text', 1)
        
        retorna int relacionado ao botaõ pressionado:        
        ok = 1
        Cancelar = 2
        Anular = 3
        Repetir = 4
        Ignorar = 5
        Yes = 6
        Não = 7
        Tentar = 10
        Continuar = 11
        
        return {IDABORT: 'abort',
                IDCANCEL: 'cancel',
                IDCONTINUE: 'continue',
                IDIGNORE: 'ignore',
                IDNO: 'no',
                IDOK: 'ok',
                IDRETRY: 'retry',
                IDTRYAGAIN: 'try again',
                IDYES: 'yes'}[result]
        
        '''
        return ctypes.windll.user32.MessageBoxW(0, text, title, style)
        
    


